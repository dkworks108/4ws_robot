#!/usr/bin/env python3
"""
ROS 2 Node for Four-Wheel Steering Kinematics, Control, and Odometry.

Bridges ROS /cmd_vel into individual steering position and wheel drive velocity commands.
Extracts measured joint states to compute least-squares forward kinematics and publish /odom and TF.
"""

import math
import os
os.environ.setdefault('PYTHONNOUSERSITE', '1')
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String
from tf2_ros import TransformBroadcaster

from four_wheel_control.kinematics import FourWheelKinematics


def yaw_to_quaternion(yaw: float):
    """Generate geometry_msgs quaternion from yaw angle."""
    half_yaw = yaw * 0.5
    return {
        'x': 0.0,
        'y': 0.0,
        'z': math.sin(half_yaw),
        'w': math.cos(half_yaw)
    }


class FourWheelKinematicsNode(Node):
    """
    Kinematics controller and odometry node for 4WS/4WD vehicle.
    """

    def __init__(self):
        super().__init__('four_wheel_kinematics_node')

        # Parameters
        self.declare_parameter('wheelbase', 0.36)
        self.declare_parameter('track_width', 0.36)
        self.declare_parameter('wheel_radius', 0.08)
        self.declare_parameter('max_steering_angle', 1.5707963)
        self.declare_parameter('max_wheel_speed', 25.0)
        self.declare_parameter('default_mode', FourWheelKinematics.MODE_B_FOUR_WHEEL)
        self.declare_parameter('cmd_vel_timeout', 0.5)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_tf', True)

        wheelbase = self.get_parameter('wheelbase').value
        track_width = self.get_parameter('track_width').value
        wheel_radius = self.get_parameter('wheel_radius').value
        max_steer = self.get_parameter('max_steering_angle').value
        max_speed = self.get_parameter('max_wheel_speed').value
        self.current_mode = self.get_parameter('default_mode').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.publish_tf = self.get_parameter('publish_tf').value

        # Kinematics engine
        self.kinematics = FourWheelKinematics(
            wheelbase=wheelbase,
            track_width=track_width,
            wheel_radius=wheel_radius,
            max_steering_angle=max_steer,
            max_wheel_speed=max_speed
        )

        # State tracking
        self.last_cmd_time = self.get_clock().now()
        self.cmd_vx = 0.0
        self.cmd_vy = 0.0
        self.cmd_wz = 0.0

        # Odometry integration state
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_yaw = 0.0
        self.last_joint_state_time: Optional[Time] = None

        # Expected joint names
        self.steer_joint_names = [
            'fl_steering_joint',
            'fr_steering_joint',
            'rl_steering_joint',
            'rr_steering_joint'
        ]
        self.wheel_joint_names = [
            'fl_wheel_joint',
            'fr_wheel_joint',
            'rl_wheel_joint',
            'rr_wheel_joint'
        ]

        # Per-wheel steering publishers (position controllers)
        self.pub_fl_steer = self.create_publisher(Float64MultiArray, 'fl_steering_controller/commands', 10)
        self.pub_fr_steer = self.create_publisher(Float64MultiArray, 'fr_steering_controller/commands', 10)
        self.pub_rl_steer = self.create_publisher(Float64MultiArray, 'rl_steering_controller/commands', 10)
        self.pub_rr_steer = self.create_publisher(Float64MultiArray, 'rr_steering_controller/commands', 10)

        # Per-wheel drive publishers (velocity controllers)
        self.pub_fl_wheel = self.create_publisher(Float64MultiArray, 'fl_wheel_controller/commands', 10)
        self.pub_fr_wheel = self.create_publisher(Float64MultiArray, 'fr_wheel_controller/commands', 10)
        self.pub_rl_wheel = self.create_publisher(Float64MultiArray, 'rl_wheel_controller/commands', 10)
        self.pub_rr_wheel = self.create_publisher(Float64MultiArray, 'rr_wheel_controller/commands', 10)

        self.pub_odom = self.create_publisher(
            Odometry,
            '/odom',
            10
        )
        self.pub_current_mode = self.create_publisher(
            String,
            '/four_wheel/current_mode',
            10
        )
        self.tf_broadcaster = TransformBroadcaster(self)

        # Subscribers
        self.sub_cmd_vel = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cb_cmd_vel,
            10
        )
        self.sub_mode = self.create_subscription(
            String,
            '/four_wheel/set_mode',
            self.cb_set_mode,
            10
        )
        self.sub_joint_states = self.create_subscription(
            JointState,
            '/joint_states',
            self.cb_joint_states,
            10
        )

        # Control loop timer (50 Hz)
        self.control_timer = self.create_timer(0.02, self.control_loop)
        # Periodic mode announce timer (2 Hz)
        self.mode_timer = self.create_timer(0.5, lambda: self.pub_current_mode.publish(String(data=self.current_mode)))

        self.get_logger().info(
            f"FourWheelKinematicsNode initialized. Mode={self.current_mode}, "
            f"L={wheelbase}m, W={track_width}m, r={wheel_radius}m"
        )

    def cb_cmd_vel(self, msg: Twist):
        """Store incoming velocity command."""
        self.last_cmd_time = self.get_clock().now()
        self.cmd_vx = msg.linear.x
        self.cmd_vy = msg.linear.y
        self.cmd_wz = msg.angular.z

    def cb_set_mode(self, msg: String):
        """Update active steering mode."""
        requested = msg.data.strip()
        if requested in FourWheelKinematics.VALID_MODES:
            self.current_mode = requested
            self.pub_current_mode.publish(String(data=self.current_mode))
            self.get_logger().info(f"Steering mode switched to: {self.current_mode}")
        else:
            self.get_logger().warn(
                f"Unknown steering mode '{requested}'. Valid modes: {FourWheelKinematics.VALID_MODES}"
            )

    def control_loop(self):
        """Periodic inverse kinematics execution and command dispatch."""
        now = self.get_clock().now()
        dt_cmd = (now - self.last_cmd_time).nanoseconds / 1e9

        if dt_cmd > self.cmd_vel_timeout:
            # Command timeout: stop robot safely
            vx, vy, wz = 0.0, 0.0, 0.0
        else:
            vx = self.cmd_vx
            vy = self.cmd_vy
            wz = self.cmd_wz

        # Compute steering positions and wheel rotational speeds
        steer_angles, wheel_speeds = self.kinematics.inverse_kinematics(
            vx=vx,
            vy=vy,
            wz=wz,
            mode=self.current_mode
        )

        # Publish steering commands (per-wheel)
        steer_pubs = [self.pub_fl_steer, self.pub_fr_steer, self.pub_rl_steer, self.pub_rr_steer]
        for pub, angle in zip(steer_pubs, steer_angles):
            msg = Float64MultiArray()
            msg.data = [float(angle)]
            pub.publish(msg)

        # Publish drive commands (per-wheel)
        drive_pubs = [self.pub_fl_wheel, self.pub_fr_wheel, self.pub_rl_wheel, self.pub_rr_wheel]
        for pub, speed in zip(drive_pubs, wheel_speeds):
            msg = Float64MultiArray()
            msg.data = [float(speed)]
            pub.publish(msg)

    def cb_joint_states(self, msg: JointState):
        """Compute forward kinematics and publish odometry from measured joints."""
        now = self.get_clock().now()
        if msg.header.stamp.sec > 0 or msg.header.stamp.nanosec > 0:
            stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        else:
            stamp_ns = now.nanoseconds

        if self.last_joint_state_time is None:
            self.last_joint_state_time = stamp_ns
            return

        dt = (stamp_ns - self.last_joint_state_time) / 1e9
        self.last_joint_state_time = stamp_ns

        if dt <= 0.0 or dt > 0.5:
            # Guard against time anomalies or large jumps
            return

        # Extract measured positions and velocities
        joint_dict = {name: (pos, vel) for name, pos, vel in zip(
            msg.name,
            msg.position if msg.position else [0.0]*len(msg.name),
            msg.velocity if msg.velocity else [0.0]*len(msg.name)
        )}

        try:
            steer_angles = [joint_dict[j][0] for j in self.steer_joint_names]
            wheel_speeds = [joint_dict[j][1] for j in self.wheel_joint_names]
        except KeyError:
            # Not all joints published yet
            return

        # Forward kinematics
        vx_body, vy_body, wz_body = self.kinematics.forward_kinematics(
            steer_angles,
            wheel_speeds
        )

        # Integrate pose in odom frame
        delta_yaw = wz_body * dt
        mid_yaw = self.odom_yaw + 0.5 * delta_yaw
        delta_x = (vx_body * math.cos(mid_yaw) - vy_body * math.sin(mid_yaw)) * dt
        delta_y = (vx_body * math.sin(mid_yaw) + vy_body * math.cos(mid_yaw)) * dt

        self.odom_x += delta_x
        self.odom_y += delta_y
        self.odom_yaw += delta_yaw

        # Normalize yaw to [-pi, pi]
        self.odom_yaw = math.atan2(math.sin(self.odom_yaw), math.cos(self.odom_yaw))

        # Build Odometry message
        odom_msg = Odometry()
        odom_msg.header.stamp = msg.header.stamp if msg.header.stamp.sec > 0 else now.to_msg()
        odom_msg.header.frame_id = self.odom_frame
        odom_msg.child_frame_id = self.base_frame

        odom_msg.pose.pose.position.x = self.odom_x
        odom_msg.pose.pose.position.y = self.odom_y
        odom_msg.pose.pose.position.z = 0.0

        q = yaw_to_quaternion(self.odom_yaw)
        odom_msg.pose.pose.orientation.x = q['x']
        odom_msg.pose.pose.orientation.y = q['y']
        odom_msg.pose.pose.orientation.z = q['z']
        odom_msg.pose.pose.orientation.w = q['w']

        # Covariances
        odom_msg.pose.covariance[0] = 0.001   # x
        odom_msg.pose.covariance[7] = 0.001   # y
        odom_msg.pose.covariance[35] = 0.002  # yaw

        odom_msg.twist.twist.linear.x = vx_body
        odom_msg.twist.twist.linear.y = vy_body
        odom_msg.twist.twist.angular.z = wz_body
        odom_msg.twist.covariance[0] = 0.001
        odom_msg.twist.covariance[7] = 0.001
        odom_msg.twist.covariance[35] = 0.002

        self.pub_odom.publish(odom_msg)

        # Publish TF odom -> base_footprint
        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = odom_msg.header.stamp
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.odom_x
            t.transform.translation.y = self.odom_y
            t.transform.translation.z = 0.0
            t.transform.rotation.x = q['x']
            t.transform.rotation.y = q['y']
            t.transform.rotation.z = q['z']
            t.transform.rotation.w = q['w']
            self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = FourWheelKinematicsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()

