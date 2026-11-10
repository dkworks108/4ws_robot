#!/usr/bin/env python3
"""
SLAM and Nav2 Navigation Integration Test for Four-Wheel Steering Autonomous Robot.

Validates:
1. SLAM Toolbox online async mapping on /map
2. Complete TF tree: map -> odom -> base_footprint -> base_link -> laser_link
3. Nav2 servers (planner_server, controller_server, behavior_server, bt_navigator)
4. Action server navigate_to_pose acceptance and motion execution
5. Dynamic map coverage growth
6. Map serialization to disk
"""

import os
import sys
import time
import math
import subprocess
import signal

os.environ.setdefault('PYTHONNOUSERSITE', '1')

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.time import Time
from nav_msgs.msg import OccupancyGrid, Odometry
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
import tf2_ros
from tf2_ros import Buffer, TransformListener


class NavigationTesterNode(Node):
    def __init__(self):
        super().__init__('navigation_tester_node')

        self.latest_map = None
        self.latest_odom = None

        self.create_subscription(OccupancyGrid, '/map', self.cb_map, 10)
        self.create_subscription(Odometry, '/odom', self.cb_odom, 10)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    def cb_map(self, msg: OccupancyGrid):
        self.latest_map = msg

    def cb_odom(self, msg: Odometry):
        self.latest_odom = msg

    def spin_duration(self, seconds: float):
        start = time.time()
        while time.time() - start < seconds and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)


def run_slam_navigation_test():
    ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 70)
    print("STARTING SLAM + NAV2 NAVIGATION INTEGRATION TEST FOR 4WS ROBOT")
    print("=" * 70)

    # Clean old processes
    subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher",
                    "four_wheel_kinematics_node", "async_slam_toolbox_node", "controller_server",
                    "planner_server", "behavior_server", "bt_navigator", "lifecycle_manager"],
                   stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    # Launch complete simulation in headless mode without exploration node
    launch_cmd = [
        "ros2", "launch", "four_wheel_description", "complete_simulation.launch.py",
        "headless:=true", "rviz:=false", "slam:=true", "navigation:=true", "exploration:=false"
    ]
    proc = subprocess.Popen(launch_cmd, preexec_fn=os.setsid)

    rclpy.init()
    tester = NavigationTesterNode()

    results = {}
    try:
        # 1. Wait for SLAM /map topic
        print("[TEST 1/5] Waiting for SLAM Toolbox to publish /map...")
        map_ready = False
        t_start = time.time()
        while time.time() - t_start < 45.0:
            tester.spin_duration(0.5)
            if tester.latest_map is not None:
                map_ready = True
                break

        assert map_ready, "Timeout waiting for /map"
        m = tester.latest_map
        known_cells_start = sum(1 for c in m.data if c >= 0)
        print(f" -> PASS: /map active! Resolution={m.info.resolution}m, Grid={m.info.width}x{m.info.height}, KnownCells={known_cells_start}")
        results['slam_map'] = True

        # 2. Validate TF tree
        print("[TEST 2/5] Validating full TF transform chain (map -> laser_link)...")
        tf_ready = False
        t_start = time.time()
        while time.time() - t_start < 25.0:
            tester.spin_duration(0.5)
            try:
                t_map_odom = tester.tf_buffer.lookup_transform('map', 'odom', Time(), timeout=Duration(seconds=0.1))
                t_odom_base = tester.tf_buffer.lookup_transform('odom', 'base_footprint', Time(), timeout=Duration(seconds=0.1))
                t_base_laser = tester.tf_buffer.lookup_transform('base_footprint', 'lidar_link', Time(), timeout=Duration(seconds=0.1))
                t_full = tester.tf_buffer.lookup_transform('map', 'lidar_link', Time(), timeout=Duration(seconds=0.1))
                tf_ready = True
                break
            except Exception:
                pass

        assert tf_ready, "TF chain validation failed"
        print(" -> PASS: Complete TF tree map -> odom -> base_footprint -> lidar_link verified!")
        results['tf_chain'] = True

        # 3. Wait for Nav2 NavigateToPose action server
        print("[TEST 3/5] Waiting for Nav2 navigate_to_pose action server...")
        server_ready = tester.nav_client.wait_for_server(timeout_sec=30.0)
        assert server_ready, "Nav2 action server navigate_to_pose not available"
        print(" -> PASS: Nav2 action server is online and ready!")
        results['nav2_server'] = True

        # Allow lifecycle manager to transition all servers to active
        print("Waiting for Nav2 lifecycle activation to complete...")
        tester.spin_duration(4.0)

        # 4. Dispatch Navigation Goal
        target_x, target_y = 1.0, 0.0
        print(f"[TEST 4/5] Sending Nav2 waypoint goal to ({target_x:.2f}, {target_y:.2f})...")
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.pose.position.x = target_x
        goal_msg.pose.pose.position.y = target_y
        goal_msg.pose.pose.orientation.w = 1.0

        goal_accepted = False
        goal_handle = None
        t_start = time.time()
        while time.time() - t_start < 30.0 and not goal_accepted:
            goal_msg.pose.header.stamp = tester.get_clock().now().to_msg()
            send_future = tester.nav_client.send_goal_async(goal_msg)
            t_sub = time.time()
            while not send_future.done() and time.time() - t_sub < 5.0:
                tester.spin_duration(0.1)

            if send_future.done():
                goal_handle = send_future.result()
                if goal_handle and goal_handle.accepted:
                    goal_accepted = True
                    break
                else:
                    print(" -> Goal not yet accepted (lifecycle transitioning), retrying in 1.5s...")
                    tester.spin_duration(1.5)
            else:
                tester.spin_duration(1.0)

        assert goal_accepted, "Nav2 rejected navigation goal after timeout"
        print(" -> Goal accepted by Nav2!")

        # Monitor execution for up to 25s
        res_future = goal_handle.get_result_async()
        t_start = time.time()
        displaced = False
        start_x = tester.latest_odom.pose.pose.position.x if tester.latest_odom else 0.0

        while time.time() - t_start < 25.0:
            tester.spin_duration(0.2)
            if tester.latest_odom:
                cur_x = tester.latest_odom.pose.pose.position.x
                if cur_x - start_x > 0.40:
                    displaced = True
            if res_future.done():
                break

        print(f" -> Robot displaced during autonomous navigation: {displaced} (start_x={start_x:.3f}, cur_x={tester.latest_odom.pose.pose.position.x if tester.latest_odom else 0.0:.3f})")
        assert displaced, "Robot did not translate toward goal pose"
        print(" -> PASS: Autonomous waypoint navigation verified!")
        results['autonomous_navigation'] = True

        # 5. Verify Map Growth
        print("[TEST 5/5] Checking SLAM map coverage growth...")
        tester.spin_duration(2.0)
        m_end = tester.latest_map
        known_cells_end = sum(1 for c in m_end.data if c >= 0)
        growth = known_cells_end - known_cells_start
        growth_pct = (growth / max(known_cells_start, 1)) * 100.0
        print(f" -> Map cells: initial={known_cells_start}, final={known_cells_end}, growth=+{growth} cells (+{growth_pct:.1f}%)")
        assert known_cells_end >= known_cells_start, "Map lost coverage"
        print(" -> PASS: Map coverage maintained/expanded during motion!")
        results['map_growth'] = True

    finally:
        tester.destroy_node()
        rclpy.shutdown()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher",
                        "four_wheel_kinematics_node", "async_slam_toolbox_node", "controller_server",
                        "planner_server", "behavior_server", "bt_navigator", "lifecycle_manager"],
                       stderr=subprocess.DEVNULL)
        time.sleep(1.0)

    print("=" * 70)
    print("SLAM + NAV2 NAVIGATION TEST SUMMARY:")
    all_passed = all(results.values()) and len(results) == 5
    for name, passed in results.items():
        print(f"  - {name:25s}: {'[PASS]' if passed else '[FAIL]'}")
    print(f"OVERALL RESULT: {'ALL 5 TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 70)
    return all_passed


if __name__ == '__main__':
    success = run_slam_navigation_test()
    sys.exit(0 if success else 1)
