#!/usr/bin/env python3
"""
Readiness Gate Helper for Master Launch Sequencing.

Waits with a bounded timeout for specific ROS 2 stage prerequisites before
allowing dependent launch stages to start:
  - stage=sim  : /clock advancing, /odom, /scan, /imu/data, 9 active controllers, odom->base_footprint TF
  - stage=slam : /map publishing and map->odom TF available
  - stage=nav2 : Nav2 lifecycle nodes ACTIVE and navigate_to_pose action server ready

Exits 0 on success, 1 on timeout/failure (halting dependent launch stages).
"""

import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONNOUSERSITE', '1')

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.time import Time

from rosgraph_msgs.msg import Clock
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan, Imu
from controller_manager_msgs.srv import ListControllers
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener


EXPECTED_CONTROLLERS = {
    'joint_state_broadcaster',
    'fl_steering_controller',
    'fr_steering_controller',
    'rl_steering_controller',
    'rr_steering_controller',
    'fl_wheel_controller',
    'fr_wheel_controller',
    'rl_wheel_controller',
    'rr_wheel_controller',
}

NAV2_NODES = ['controller_server', 'planner_server', 'behavior_server', 'bt_navigator']


class LaunchGateNode(Node):
    def __init__(self, stage: str):
        super().__init__(f'launch_gate_{stage}')
        self.stage = stage
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.got_clock = False
        self.last_clock = -1.0
        self.clock_ticks = 0
        self.got_odom = False
        self.got_scan = False
        self.got_imu = False
        self.got_map = False
        self.controllers_ok = False
        self.tf_ok = False
        self.nav2_ok = False
        self._last_ctrl_query = 0.0
        self._last_nav2_query = 0.0
        self._odom_first_seen = 0.0

        if stage == 'sim':
            self.create_subscription(Clock, '/clock', self._cb_clock, 10)
            self.create_subscription(Odometry, '/odom', self._cb_odom, 10)
            self.create_subscription(LaserScan, '/scan', self._cb_scan, 10)
            self.create_subscription(Imu, '/imu/data', self._cb_imu, 10)
            self.cli_ctrl = self.create_client(ListControllers, '/controller_manager/list_controllers')
            self._ctrl_future = None
        elif stage == 'slam':
            self.create_subscription(OccupancyGrid, '/map', self._cb_map, 10)
        elif stage == 'nav2':
            self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
            self.state_clients = {
                n: self.create_client(GetState, f'/{n}/get_state') for n in NAV2_NODES
            }
            self.state_vals = {}
            self.state_futures = {}

    def _cb_clock(self, msg: Clock):
        val = msg.clock.sec + msg.clock.nanosec * 1e-9
        if self.last_clock >= 0.0 and val > self.last_clock:
            self.clock_ticks += 1
            if self.clock_ticks >= 2:
                self.got_clock = True
        self.last_clock = val

    def _cb_odom(self, msg: Odometry):
        if not self.got_odom:
            self._odom_first_seen = time.monotonic()
        self.got_odom = True

    def _cb_scan(self, msg: LaserScan):
        if len(msg.ranges) > 0:
            self.got_scan = True

    def _cb_imu(self, msg: Imu):
        self.got_imu = True

    def _cb_map(self, msg: OccupancyGrid):
        if msg.info.width > 0 and msg.info.height > 0:
            self.got_map = True

    def step_check(self) -> bool:
        now = time.monotonic()
        if self.stage == 'sim':
            if not self.controllers_ok:
                if self._ctrl_future is not None and self._ctrl_future.done():
                    try:
                        resp = self._ctrl_future.result()
                        active = {c.name for c in resp.controller if c.state == 'active'}
                        if EXPECTED_CONTROLLERS.issubset(active):
                            self.controllers_ok = True
                    except Exception:
                        pass
                    self._ctrl_future = None
                elif (
                    self._ctrl_future is None
                    and self.got_odom
                    and (now - self._odom_first_seen) >= 2.5
                    and (now - self._last_ctrl_query) >= 2.0
                    and self.cli_ctrl.service_is_ready()
                ):
                    self._last_ctrl_query = now
                    self._ctrl_future = self.cli_ctrl.call_async(ListControllers.Request())

            if not self.tf_ok:
                try:
                    self.tf_buffer.lookup_transform(
                        'odom', 'base_footprint', Time(), timeout=Duration(seconds=0.0)
                    )
                    self.tf_ok = True
                except Exception:
                    pass

            return (
                self.got_clock
                and self.got_odom
                and self.got_scan
                and self.got_imu
                and self.controllers_ok
                and self.tf_ok
            )

        if self.stage == 'slam':
            if not self.tf_ok:
                try:
                    self.tf_buffer.lookup_transform(
                        'map', 'odom', Time(), timeout=Duration(seconds=0.0)
                    )
                    self.tf_ok = True
                except Exception:
                    pass
            return self.got_map and self.tf_ok

        if self.stage == 'nav2':
            for n, cli in self.state_clients.items():
                fut = self.state_futures.get(n)
                if fut is not None and fut.done():
                    try:
                        self.state_vals[n] = fut.result().current_state.id
                    except Exception:
                        pass
                    self.state_futures[n] = None
                elif fut is None and (now - self._last_nav2_query) >= 1.5 and cli.service_is_ready():
                    self.state_futures[n] = cli.call_async(GetState.Request())
            if (now - self._last_nav2_query) >= 1.5:
                self._last_nav2_query = now

            all_active = all(self.state_vals.get(n) == 3 for n in NAV2_NODES)
            action_ready = self.nav_client.server_is_ready()
            self.nav2_ok = all_active and action_ready
            return self.nav2_ok

        return False

    def missing_summary(self) -> str:
        if self.stage == 'sim':
            missing = []
            if not self.got_clock:
                missing.append('/clock')
            if not self.controllers_ok:
                missing.append('ros2_control(9 controllers)')
            if not self.got_odom:
                missing.append('/odom')
            if not self.got_scan:
                missing.append('/scan')
            if not self.got_imu:
                missing.append('/imu/data')
            if not self.tf_ok:
                missing.append('TF(odom->base_footprint)')
            return ', '.join(missing)
        if self.stage == 'slam':
            missing = []
            if not self.got_map:
                missing.append('/map')
            if not self.tf_ok:
                missing.append('TF(map->odom)')
            return ', '.join(missing)
        if self.stage == 'nav2':
            inactive = [n for n in NAV2_NODES if self.state_vals.get(n) != 3]
            if not self.nav_client.server_is_ready():
                inactive.append('navigate_to_pose_action')
            return ', '.join(inactive)
        return ''


def main():
    parser = argparse.ArgumentParser(description='ROS 2 launch readiness gate')
    parser.add_argument('--stage', required=True, choices=['sim', 'slam', 'nav2'])
    parser.add_argument('--timeout', type=float, default=45.0)
    args, unknown = parser.parse_known_args()

    rclpy.init(args=unknown)
    node = LaunchGateNode(args.stage)
    start = time.monotonic()
    last_log = 0.0
    exit_code = 1

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.step_check():
                node.get_logger().info(f"[GATE:{args.stage.upper()}] PASSED in {time.monotonic() - start:.1f}s")
                exit_code = 0
                break

            elapsed = time.monotonic() - start
            if elapsed - last_log >= 5.0:
                last_log = elapsed
                node.get_logger().info(
                    f"[GATE:{args.stage.upper()}] Waiting ({elapsed:.0f}/{args.timeout:.0f}s) for: {node.missing_summary()}"
                )
            if elapsed >= args.timeout:
                node.get_logger().error(
                    f"[GATE:{args.stage.upper()}] FAILED after {args.timeout:.0f}s! Missing: {node.missing_summary()}"
                )
                exit_code = 1
                break
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
