#!/usr/bin/env python3
"""
Central Command Arbiter & Safety Multiplexer for Four-Wheel Steering Robot.

Enforces strict single-authority command execution between:
1. Mobile Virtual Joystick (MANUAL mode)
2. Nav2 Autonomous Navigation (AUTONOMOUS_NAV mode)
3. Frontier Exploration (AUTONOMOUS_EXPLORE mode)
4. Emergency Stop (ESTOP mode - absolute highest priority)

Features:
- Hardware/software watchdog with automatic zero-velocity timeout.
- Browser disconnect auto-stop.
- Speed limit scaling (25%, 50%, 75%, 100%).
- Safe mode transitions with zero-velocity injection.
- Nav2 goal cancellation and exploration pause on E-stop or mode change.
- JSON status publishing on /mobile/arbiter_status.
"""

import os
import sys
import json
import math
import time
from typing import Optional

os.environ.setdefault('PYTHONNOUSERSITE', '1')

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Bool, Float32, Empty
from std_srvs.srv import Trigger, SetBool
from action_msgs.srv import CancelGoal

# Nav2 action client for goal cancellation
try:
    from nav2_msgs.action import NavigateToPose
    NAV2_AVAILABLE = True
except ImportError:
    NAV2_AVAILABLE = False


class CommandArbiterNode(Node):
    """
    Central velocity multiplexer and authority manager.
    """

    MODE_MANUAL = "MANUAL"
    MODE_NAV = "AUTONOMOUS_NAV"
    MODE_EXPLORE = "AUTONOMOUS_EXPLORE"
    MODE_ESTOP = "ESTOP"

    VALID_MODES = [MODE_MANUAL, MODE_NAV, MODE_EXPLORE, MODE_ESTOP]

    def __init__(self):
        super().__init__('command_arbiter_node')

        # Parameters
        self.declare_parameter('default_mode', self.MODE_MANUAL)
        self.declare_parameter('watchdog_timeout', 0.40)     # seconds (monotonic)
        self.declare_parameter('heartbeat_timeout', 1.20)    # seconds (monotonic)
        self.declare_parameter('default_speed_limit', 1.0)   # 1.0 = 100%
        self.declare_parameter('max_linear_vel', 1.5)        # m/s safety ceiling
        self.declare_parameter('max_angular_vel', 2.0)       # rad/s safety ceiling

        self.current_mode = self.get_parameter('default_mode').value
        self.watchdog_timeout = float(self.get_parameter('watchdog_timeout').value)
        self.heartbeat_timeout = float(self.get_parameter('heartbeat_timeout').value)
        self.speed_limit = float(self.get_parameter('default_speed_limit').value)
        self.max_linear_vel = float(self.get_parameter('max_linear_vel').value)
        self.max_angular_vel = float(self.get_parameter('max_angular_vel').value)

        # Internal state (using monotonic wall clock so paused /clock cannot defeat safety)
        self.estop_active = False
        self.last_manual_cmd_time = 0.0
        self.last_heartbeat_time = 0.0
        self._heartbeat_seen = False
        self.manual_twist = Twist()
        self.nav_twist = Twist()
        self.last_nav_cmd_time = 0.0
        self.mode_transition_time = 0.0
        self.watchdog_tripped = False
        self.active_authority = "none"

        # Output publisher -> directly to kinematics controller
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)

        # Status publishers
        self.pub_status = self.create_publisher(String, '/mobile/arbiter_status', 10)
        self.pub_estop_status = self.create_publisher(Bool, '/mobile/estop_status', 10)

        # Subscribers
        self.sub_manual = self.create_subscription(
            Twist, '/mobile/cmd_vel', self.cb_manual_cmd, 10
        )
        self.sub_nav = self.create_subscription(
            Twist, '/cmd_vel_nav', self.cb_nav_cmd, 10
        )
        self.sub_heartbeat = self.create_subscription(
            Empty, '/mobile/heartbeat', self.cb_heartbeat, 10
        )
        self.sub_set_mode = self.create_subscription(
            String, '/mobile/set_mode', self.cb_set_mode_topic, 10
        )
        self.sub_estop_topic = self.create_subscription(
            Bool, '/mobile/estop', self.cb_estop_topic, 10
        )
        self.sub_speed_limit = self.create_subscription(
            Float32, '/mobile/set_speed_limit', self.cb_speed_limit_topic, 10
        )

        # Services
        self.srv_estop = self.create_service(Trigger, '/mobile/trigger_estop', self.cb_trigger_estop)
        self.srv_reset_estop = self.create_service(Trigger, '/mobile/reset_estop', self.cb_reset_estop)

        # Exploration service clients for coordination
        self.cli_expl_pause = self.create_client(Trigger, '/exploration/pause')
        self.cli_expl_stop = self.create_client(Trigger, '/exploration/stop')
        self.cli_expl_resume = self.create_client(Trigger, '/exploration/resume')

        # Nav2 Action Cancel Service Client (cancels goals from any client)
        self.cli_nav_cancel = self.create_client(CancelGoal, 'navigate_to_pose/_action/cancel_goal')
        if NAV2_AVAILABLE:
            self.nav2_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        else:
            self.nav2_client = None

        # Control Loop Timer (50 Hz)
        self.loop_timer = self.create_timer(0.02, self.control_cycle)
        # Status Publish Timer (10 Hz)
        self.status_timer = self.create_timer(0.10, self.publish_status)

        self.get_logger().info(
            f"CommandArbiterNode initialized. Initial Mode: {self.current_mode}, "
            f"Speed Limit: {int(self.speed_limit*100)}%, Watchdog: {self.watchdog_timeout}s (monotonic)"
        )

    def cb_manual_cmd(self, msg: Twist):
        """Receive virtual joystick velocity command."""
        self.last_manual_cmd_time = time.monotonic()
        self.manual_twist = msg

    def cb_nav_cmd(self, msg: Twist):
        """Receive autonomous navigation velocity command."""
        self.last_nav_cmd_time = time.monotonic()
        self.nav_twist = msg

    def cb_heartbeat(self, msg: Empty):
        """Keep-alive heartbeat from mobile browser (does NOT extend stale cmd_vel)."""
        self.last_heartbeat_time = time.monotonic()
        self._heartbeat_seen = True

    def cb_set_mode_topic(self, msg: String):
        """Handle mode switch request via topic."""
        req_mode = msg.data.strip().upper()
        self.switch_mode(req_mode)

    def cb_estop_topic(self, msg: Bool):
        """Handle E-Stop state via boolean topic."""
        if msg.data:
            self.trigger_estop("E-Stop commanded via /mobile/estop")
        else:
            self.reset_estop("E-Stop reset via /mobile/estop")

    def cb_speed_limit_topic(self, msg: Float32):
        """Handle speed limit adjustment (0.25, 0.5, 0.75, 1.0)."""
        limit = float(msg.data)
        if 0.1 <= limit <= 1.0:
            self.speed_limit = limit
            self.get_logger().info(f"Speed limit set to {int(self.speed_limit*100)}%")

    def cb_trigger_estop(self, request, response):
        """Service callback to trigger E-Stop."""
        self.trigger_estop("Triggered via ROS service /mobile/trigger_estop")
        response.success = True
        response.message = "EMERGENCY STOP ACTIVATED."
        return response

    def cb_reset_estop(self, request, response):
        """Service callback to reset E-Stop."""
        self.reset_estop("Reset via ROS service /mobile/reset_estop")
        response.success = True
        response.message = "Emergency stop cleared. Switched to safe MANUAL mode."
        return response

    def trigger_estop(self, reason: str):
        """Latching emergency stop execution."""
        self.estop_active = True
        self.current_mode = self.MODE_ESTOP
        self.manual_twist = Twist()
        self.nav_twist = Twist()
        self.last_manual_cmd_time = 0.0
        self.last_nav_cmd_time = 0.0
        self.active_authority = "estop"
        self.publish_zero_velocity()
        self.cancel_active_navigation_goals()
        self.pause_exploration()
        self.get_logger().warn(f"🚨 EMERGENCY STOP ENGAGED: {reason}")

    def reset_estop(self, reason: str):
        """Disengage emergency stop and return to safe MANUAL state requiring fresh command."""
        self.estop_active = False
        self.current_mode = self.MODE_MANUAL
        self.manual_twist = Twist()
        self.nav_twist = Twist()
        self.last_manual_cmd_time = 0.0
        self.last_nav_cmd_time = 0.0
        self.watchdog_tripped = False
        self.active_authority = "none"
        self.publish_zero_velocity()
        self.mode_transition_time = time.monotonic()
        self.get_logger().info(f"✅ EMERGENCY STOP CLEARED: {reason} -> Switched to MANUAL mode (fresh command required).")

    def switch_mode(self, new_mode: str):
        """Perform verified ownership transition between operating modes."""
        if self.estop_active and new_mode != self.MODE_ESTOP:
            self.get_logger().warn(
                f"Cannot switch to {new_mode} while EMERGENCY STOP is engaged. Reset E-Stop first."
            )
            return

        if new_mode not in self.VALID_MODES:
            self.get_logger().warn(f"Invalid mode '{new_mode}'. Allowed: {self.VALID_MODES}")
            return

        if new_mode == self.current_mode:
            return

        prev_mode = self.current_mode
        self.current_mode = new_mode
        self.mode_transition_time = time.monotonic()

        # Clear stale twists across mode boundaries
        self.manual_twist = Twist()
        self.nav_twist = Twist()
        self.last_manual_cmd_time = 0.0
        self.last_nav_cmd_time = 0.0

        # Inject safe zero-velocity during transition
        self.publish_zero_velocity()

        # Handle departure actions
        if prev_mode == self.MODE_NAV and new_mode != self.MODE_NAV:
            self.cancel_active_navigation_goals()

        if prev_mode == self.MODE_EXPLORE and new_mode != self.MODE_EXPLORE:
            self.pause_exploration()

        self.get_logger().info(f"🔄 Mode Transition: [{prev_mode}] -> [{self.current_mode}]")

    def cancel_active_navigation_goals(self):
        """Cancel all in-flight Nav2 NavigateToPose action goals via ROS 2 CancelGoal service."""
        if self.cli_nav_cancel.service_is_ready():
            try:
                req = CancelGoal.Request()
                # Empty goal_info (zero UUID & zero stamp) cancels ALL active goals
                self.cli_nav_cancel.call_async(req)
                self.get_logger().info("Sent CancelGoal request to Nav2 navigate_to_pose.")
            except Exception as e:
                self.get_logger().warn(f"Nav2 goal cancel error: {e}")

    def pause_exploration(self):
        """Call exploration pause service."""
        if self.cli_expl_pause.service_is_ready():
            req = Trigger.Request()
            self.cli_expl_pause.call_async(req)

    def publish_zero_velocity(self):
        """Immediately emit zero velocity command to physical/sim base."""
        zero_twist = Twist()
        self.pub_cmd_vel.publish(zero_twist)

    def control_cycle(self):
        """High-frequency periodic command arbitration loop (50 Hz)."""
        now_mono = time.monotonic()

        # Absolute E-Stop override
        if self.estop_active or self.current_mode == self.MODE_ESTOP:
            self.active_authority = "estop"
            self.publish_zero_velocity()
            return

        # Safe transition lockout: hold zero velocity for 0.15s upon mode change
        if (now_mono - self.mode_transition_time) < 0.15:
            self.active_authority = "transition_lockout"
            self.publish_zero_velocity()
            return

        out_twist = Twist()
        active_authority = "none"

        if self.current_mode == self.MODE_MANUAL:
            dt_manual = now_mono - self.last_manual_cmd_time
            heartbeat_stale = (
                self._heartbeat_seen and (now_mono - self.last_heartbeat_time) > self.heartbeat_timeout
            )

            if self.last_manual_cmd_time <= 0.0 or dt_manual > self.watchdog_timeout or heartbeat_stale:
                # Watchdog tripped: mobile client disconnected, stale cmd_vel, or joystick idle
                self.watchdog_tripped = (self.last_manual_cmd_time > 0.0)
                active_authority = "watchdog_stop"
                out_twist = Twist()  # zero velocity
            else:
                self.watchdog_tripped = False
                active_authority = "mobile_joystick"
                # Apply speed limit scaling & safety clamping
                scale = self.speed_limit
                vx = self.manual_twist.linear.x * scale
                vy = self.manual_twist.linear.y * scale
                wz = self.manual_twist.angular.z * scale

                # Clamp to safety limits
                out_twist.linear.x = max(-self.max_linear_vel, min(self.max_linear_vel, vx))
                out_twist.linear.y = max(-self.max_linear_vel, min(self.max_linear_vel, vy))
                out_twist.angular.z = max(-self.max_angular_vel, min(self.max_angular_vel, wz))

        elif self.current_mode in (self.MODE_NAV, self.MODE_EXPLORE):
            dt_nav = now_mono - self.last_nav_cmd_time

            if self.last_nav_cmd_time <= 0.0 or dt_nav > 0.50:
                # Nav2 paused or inactive
                active_authority = "nav_idle"
                out_twist = Twist()
            else:
                active_authority = "nav2" if self.current_mode == self.MODE_NAV else "explorer"
                out_twist = Twist()
                out_twist.linear.x = max(-self.max_linear_vel, min(self.max_linear_vel, self.nav_twist.linear.x))
                out_twist.linear.y = max(-self.max_linear_vel, min(self.max_linear_vel, self.nav_twist.linear.y))
                out_twist.angular.z = max(-self.max_angular_vel, min(self.max_angular_vel, self.nav_twist.angular.z))

        self.active_authority = active_authority
        # Publish the arbitrated command to the kinematics controller
        self.pub_cmd_vel.publish(out_twist)

    def publish_status(self):
        """Emit telemetry state JSON to /mobile/arbiter_status."""
        now_mono = time.monotonic()
        heartbeat_alive = (
            self._heartbeat_seen and (now_mono - self.last_heartbeat_time) <= self.heartbeat_timeout
        )
        status_dict = {
            "operating_mode": self.current_mode,
            "active_authority": self.active_authority,
            "estop_active": self.estop_active,
            "speed_limit": self.speed_limit,
            "speed_limit_pct": int(self.speed_limit * 100),
            "watchdog_tripped": self.watchdog_tripped,
            "heartbeat_alive": heartbeat_alive,
            "valid_modes": self.VALID_MODES,
            "timestamp": self.get_clock().now().nanoseconds / 1e9
        }
        msg = String()
        msg.data = json.dumps(status_dict)
        self.pub_status.publish(msg)

        msg_estop = Bool()
        msg_estop.data = self.estop_active
        self.pub_estop_status.publish(msg_estop)


def main(args=None):
    rclpy.init(args=args)
    node = CommandArbiterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_zero_velocity()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

