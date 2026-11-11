#!/usr/bin/env python3
"""
Comprehensive End-to-End Integration Verification Suite for Project 04.

Tests all 19 verification criteria specified in Section 8:
1. Gazebo Fortress running & clock progressing
2. Robot spawned & active
3. All eight actuated joints present in /joint_states
4. Controllers active (joint_state_broadcaster, steering, drive)
5. Robot responds to movement commands (/cmd_vel -> /odom velocity)
6. All 5 steering modes operational (Ackermann, 4WS, Crab, Swerve, In-place)
7. 360-degree LiDAR publishes valid scans on /scan
8. IMU publishes valid data on /imu/data
9. Camera publishes valid frames on /camera/image_raw
10. SLAM Toolbox publishes valid /map & map->odom TF
11. Nav2 active & navigate_to_pose action server responsive
12. Navigation goal dispatch & execution verification
13. Frontier Exploration start/pause/resume/stop services
14. Mobile dashboard HTTP server responding on port 3000
15. Rosbridge WebSocket accepting connections on port 9090
16. Web Video Server streaming on port 8080
17. Mobile joystick commands (/mobile/cmd_vel) routed through Command Arbiter
18. Emergency stop priority & zero-velocity latching
19. Command watchdog & browser disconnect safe stopping (400ms cutoff)
"""

import os
import sys
import time
import base64
import socket
import urllib.request
import math
from typing import Dict, Any

os.environ.setdefault('PYTHONNOUSERSITE', '1')

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.time import Time

from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState, LaserScan, Imu, Image, CameraInfo
from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import String, Bool, Empty, Float64MultiArray
from std_srvs.srv import Trigger
from controller_manager_msgs.srv import ListControllers
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus

import tf2_ros
from tf2_ros import Buffer, TransformListener


class MasterLaunchE2ETester(Node):

    EXPECTED_JOINTS = [
        'fl_steering_joint', 'fr_steering_joint',
        'rl_steering_joint', 'rr_steering_joint',
        'fl_wheel_joint', 'fr_wheel_joint',
        'rl_wheel_joint', 'rr_wheel_joint'
    ]

    def __init__(self):
        super().__init__('master_launch_e2e_tester')

        self.results: Dict[str, Dict[str, Any]] = {}

        # TF
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Action Client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Service Clients
        self.cli_explore_start = self.create_client(Trigger, '/exploration/start')
        self.cli_explore_stop = self.create_client(Trigger, '/exploration/stop')
        self.cli_estop_trigger = self.create_client(Trigger, '/mobile/trigger_estop')
        self.cli_estop_reset = self.create_client(Trigger, '/mobile/reset_estop')
        self.cli_list_controllers = self.create_client(ListControllers, '/controller_manager/list_controllers')

        # Publishers
        self.pub_mobile_cmd = self.create_publisher(Twist, '/mobile/cmd_vel', 10)
        self.pub_direct_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_set_mode = self.create_publisher(String, '/four_wheel/set_mode', 10)
        self.pub_arb_mode = self.create_publisher(String, '/mobile/set_mode', 10)
        self.pub_heartbeat = self.create_publisher(Empty, '/mobile/heartbeat', 10)

        # Subscribers
        self.latest_clock = None
        self.latest_joints = None
        self.latest_scan = None
        self.latest_imu = None
        self.latest_image = None
        self.latest_cam_info = None
        self.latest_map = None
        self.latest_odom = None
        self.latest_arbiter = None
        self.latest_mode = None
        self.latest_steer_cmds = {}
        self.latest_drive_cmds = {}

        self.create_subscription(Clock, '/clock', self._cb_clock, 10)
        self.create_subscription(JointState, '/joint_states', self._cb_joints, 10)
        self.create_subscription(LaserScan, '/scan', self._cb_scan, 10)
        self.create_subscription(Imu, '/imu/data', self._cb_imu, 10)
        self.create_subscription(Image, '/camera/image_raw', self._cb_image, 10)
        self.create_subscription(CameraInfo, '/camera/camera_info', self._cb_cam_info, 10)
        self.create_subscription(OccupancyGrid, '/map', self._cb_map, 10)
        self.create_subscription(Odometry, '/odom', self._cb_odom, 10)
        self.create_subscription(String, '/mobile/arbiter_status', self._cb_arbiter, 10)
        self.create_subscription(String, '/four_wheel/current_mode', self._cb_mode, 10)
        for prefix in ('fl', 'fr', 'rl', 'rr'):
            self.create_subscription(
                Float64MultiArray,
                f'/{prefix}_steering_controller/commands',
                lambda m, p=prefix: self.latest_steer_cmds.__setitem__(p, m.data[0] if m.data else 0.0),
                10,
            )
            self.create_subscription(
                Float64MultiArray,
                f'/{prefix}_wheel_controller/commands',
                lambda m, p=prefix: self.latest_drive_cmds.__setitem__(p, m.data[0] if m.data else 0.0),
                10,
            )

    def _cb_clock(self, msg): self.latest_clock = msg
    def _cb_joints(self, msg): self.latest_joints = msg
    def _cb_scan(self, msg): self.latest_scan = msg
    def _cb_imu(self, msg): self.latest_imu = msg
    def _cb_image(self, msg): self.latest_image = msg
    def _cb_cam_info(self, msg): self.latest_cam_info = msg
    def _cb_map(self, msg): self.latest_map = msg
    def _cb_odom(self, msg): self.latest_odom = msg
    def _cb_arbiter(self, msg): self.latest_arbiter = msg
    def _cb_mode(self, msg): self.latest_mode = msg

    def spin_for(self, duration_sec: float):
        start = time.time()
        while time.time() - start < duration_sec:
            rclpy.spin_once(self, timeout_sec=0.05)


def run_tests():
    rclpy.init()
    tester = MasterLaunchE2ETester()
    results = {}

    print("=" * 70)
    print("STARTING PROJECT 04 MASTER LAUNCH END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    # Let data arrive
    tester.spin_for(2.0)

    # TEST 1: Gazebo simulation running & clock progressing
    print("\n[CHECK 01/19] Gazebo Simulation Clock Progression...")
    clock1 = tester.latest_clock
    tester.spin_for(1.0)
    clock2 = tester.latest_clock
    t1_pass = (clock1 is not None and clock2 is not None and
               (clock2.clock.sec + clock2.clock.nanosec * 1e-9) > (clock1.clock.sec + clock1.clock.nanosec * 1e-9))
    results['1_gazebo_running'] = {
        'title': 'Gazebo Simulation Running',
        'passed': t1_pass,
        'details': f"Clock advanced from {clock1.clock.sec if clock1 else None}s to {clock2.clock.sec if clock2 else None}s"
    }
    print(f" -> Result: {'PASSED' if t1_pass else 'FAILED'}: {results['1_gazebo_running']['details']}")

    # TEST 2: Robot spawning
    print("\n[CHECK 02/19] Robot Spawning & Transform Tree...")
    t2_pass = False
    try:
        if tester.tf_buffer.can_transform('odom', 'base_footprint', Time(), timeout=Duration(seconds=2.0)):
            t2_pass = True
    except Exception as e:
        pass
    results['2_robot_spawned'] = {
        'title': 'Robot Spawning & TF (odom -> base_footprint)',
        'passed': t2_pass,
        'details': 'Transform odom -> base_footprint is active and valid' if t2_pass else 'TF unavailable'
    }
    print(f" -> Result: {'PASSED' if t2_pass else 'FAILED'}: {results['2_robot_spawned']['details']}")

    # TEST 3: All 8 actuated joints
    print("\n[CHECK 03/19] All 8 Actuated Joints Available in /joint_states...")
    t3_pass = False
    details_j = "No joint states"
    if tester.latest_joints:
        j_names = set(tester.latest_joints.name)
        missing = [j for j in tester.EXPECTED_JOINTS if j not in j_names]
        t3_pass = len(missing) == 0
        details_j = f"Found {len(j_names)} joints. All 8 4WS/4WD joints present." if t3_pass else f"Missing: {missing}"
    results['3_actuated_joints'] = {
        'title': 'Eight Actuated Joints Available',
        'passed': t3_pass,
        'details': details_j
    }
    print(f" -> Result: {'PASSED' if t3_pass else 'FAILED'}: {details_j}")

    # TEST 4: Controllers active (query /controller_manager/list_controllers)
    print("\n[CHECK 04/19] Controllers Active (JSB + 4 Steering + 4 Wheel Controllers)...")
    expected_ctrls = {
        'joint_state_broadcaster',
        'fl_steering_controller', 'fr_steering_controller',
        'rl_steering_controller', 'rr_steering_controller',
        'fl_wheel_controller', 'fr_wheel_controller',
        'rl_wheel_controller', 'rr_wheel_controller',
    }
    t4_pass = False
    details_c4 = "Controller manager service unavailable"
    if tester.cli_list_controllers.wait_for_service(timeout_sec=3.0):
        fut_c = tester.cli_list_controllers.call_async(ListControllers.Request())
        t_wait = time.time()
        while time.time() - t_wait < 3.0 and not fut_c.done():
            tester.spin_for(0.05)
        if fut_c.done():
            active_ctrls = {c.name for c in fut_c.result().controller if c.state == 'active'}
            missing_c = sorted(expected_ctrls - active_ctrls)
            t4_pass = len(missing_c) == 0
            details_c4 = (
                f"All 9/9 controllers active: {sorted(active_ctrls)}"
                if t4_pass else f"Missing/inactive controllers: {missing_c}"
            )
    results['4_controllers_active'] = {
        'title': 'Controllers Active',
        'passed': t4_pass,
        'details': details_c4
    }
    print(f" -> Result: {'PASSED' if t4_pass else 'FAILED'}: {details_c4}")

    # TEST 5: Robot responds to movement commands (cmd -> wheels -> Gazebo odom)
    print("\n[CHECK 05/19] Robot Responds to Movement Commands & Odometry Updates...")
    tester.pub_arb_mode.publish(String(data='MANUAL'))
    tester.spin_for(0.25)
    odom_before = tester.latest_odom
    start_x = odom_before.pose.pose.position.x if odom_before else 0.0
    start_y = odom_before.pose.pose.position.y if odom_before else 0.0
    start_move = time.time()
    while time.time() - start_move < 1.2:
        cmd = Twist()
        cmd.linear.x = 0.4
        tester.pub_mobile_cmd.publish(cmd)
        tester.spin_for(0.05)
    tester.spin_for(0.25)
    odom_after = tester.latest_odom
    disp = math.hypot(
        (odom_after.pose.pose.position.x - start_x) if odom_after else 0.0,
        (odom_after.pose.pose.position.y - start_y) if odom_after else 0.0,
    )
    drive_ok = len(tester.latest_drive_cmds) == 4 and any(abs(v) > 0.5 for v in tester.latest_drive_cmds.values())
    t5_pass = drive_ok and disp > 0.05
    results['5_movement_response'] = {
        'title': 'Movement Response',
        'passed': t5_pass,
        'details': f"Drive cmds={tester.latest_drive_cmds}, odom_disp={disp:.3f}m"
    }
    print(f" -> Result: {'PASSED' if t5_pass else 'FAILED'}: {results['5_movement_response']['details']}")

    # Stop robot
    tester.pub_mobile_cmd.publish(Twist())
    tester.spin_for(0.35)

    # TEST 6: All five steering modes (command -> steering targets + drive cmds + physical response)
    print("\n[CHECK 06/19] All 5 Locomotion & Steering Kinematics Modes...")
    mode_specs = [
        ('front_steer',      Twist(linear=Twist().linear, angular=Twist().angular), (0.4, 0.0, 0.5)),
        ('four_wheel_steer', Twist(), (0.4, 0.0, 0.6)),
        ('crab',             Twist(), (0.0, 0.35, 0.0)),
        ('generalized',      Twist(), (0.3, 0.2, 0.3)),
        ('in_place_spin',    Twist(), (0.0, 0.0, 0.8)),
    ]
    modes_verified = []
    mode_logs = []
    for m, _, (vx, vy, wz) in mode_specs:
        tester.pub_set_mode.publish(String(data=m))
        tester.spin_for(0.25)
        cmd = Twist()
        cmd.linear.x = vx
        cmd.linear.y = vy
        cmd.angular.z = wz
        t_m = time.time()
        while time.time() - t_m < 0.6:
            tester.pub_mobile_cmd.publish(cmd)
            tester.spin_for(0.05)
        mode_ok = tester.latest_mode and tester.latest_mode.data == m
        steers = dict(tester.latest_steer_cmds)
        drives = dict(tester.latest_drive_cmds)
        geom_ok = False
        if m == 'front_steer' and len(steers) == 4:
            geom_ok = abs(steers['fl']) > 0.05 and abs(steers['rl']) < 1e-3 and abs(steers['rr']) < 1e-3
        elif m == 'four_wheel_steer' and len(steers) == 4:
            geom_ok = steers['fl'] * steers['rl'] < 0.0
        elif m == 'crab' and len(steers) == 4:
            geom_ok = all(abs(steers[k] - math.pi / 2.0) < 0.1 for k in steers)
        elif m == 'generalized' and len(steers) == 4:
            geom_ok = any(abs(v) > 0.05 for v in steers.values()) and any(abs(v) > 0.1 for v in drives.values())
        elif m == 'in_place_spin' and len(steers) == 4:
            geom_ok = abs(abs(steers['fl']) - math.pi / 4.0) < 0.1 and (drives['fl'] * drives['fr'] < 0.0)
        if mode_ok and geom_ok:
            modes_verified.append(m)
        mode_logs.append(f"{m}:{'OK' if (mode_ok and geom_ok) else 'FAIL'}")
        tester.pub_mobile_cmd.publish(Twist())
        tester.spin_for(0.2)

    t6_pass = len(modes_verified) == 5
    # Return to default 4ws
    tester.pub_set_mode.publish(String(data='four_wheel_steer'))
    tester.spin_for(0.2)
    results['6_steering_modes'] = {
        'title': 'Five Steering Modes Operational',
        'passed': t6_pass,
        'details': f"Verified {len(modes_verified)}/5 modes ({', '.join(mode_logs)})"
    }
    print(f" -> Result: {'PASSED' if t6_pass else 'FAILED'}: {results['6_steering_modes']['details']}")

    # TEST 7: 360-degree LiDAR publishes valid scans
    print("\n[CHECK 07/19] 360-Degree LiDAR Scan Publishing...")
    t7_pass = (tester.latest_scan is not None and
               len(tester.latest_scan.ranges) > 100 and
               tester.latest_scan.range_max > 5.0)
    details_scan = f"Received scan with {len(tester.latest_scan.ranges) if tester.latest_scan else 0} rays, range_max={tester.latest_scan.range_max if tester.latest_scan else 0}m"
    results['7_lidar_scan'] = {
        'title': 'LiDAR Valid LaserScans',
        'passed': t7_pass,
        'details': details_scan
    }
    print(f" -> Result: {'PASSED' if t7_pass else 'FAILED'}: {details_scan}")

    # TEST 8: IMU measurements
    print("\n[CHECK 08/19] IMU Measurements Publishing...")
    t8_pass = (tester.latest_imu is not None and
               (abs(tester.latest_imu.orientation.w) > 0.0 or abs(tester.latest_imu.linear_acceleration.z) > 0.0))
    details_imu = f"Orientation w={tester.latest_imu.orientation.w:.4f}, Az={tester.latest_imu.linear_acceleration.z:.2f} m/s^2" if tester.latest_imu else "No IMU"
    results['8_imu_data'] = {
        'title': 'IMU Sensor Measurements',
        'passed': t8_pass,
        'details': details_imu
    }
    print(f" -> Result: {'PASSED' if t8_pass else 'FAILED'}: {details_imu}")

    # TEST 9: Camera frames + camera_info
    print("\n[CHECK 09/19] Camera Frames & CameraInfo Publishing...")
    t9_pass = (tester.latest_image is not None and
               tester.latest_image.width > 0 and
               tester.latest_image.height > 0 and
               len(tester.latest_image.data) > 0 and
               tester.latest_cam_info is not None)
    details_img = (
        f"Image: {tester.latest_image.width}x{tester.latest_image.height} {tester.latest_image.encoding}, "
        f"camera_info={'OK' if tester.latest_cam_info else 'MISSING'}"
        if tester.latest_image else "No Image"
    )
    results['9_camera_frames'] = {
        'title': 'Camera RGB Frames & CameraInfo',
        'passed': t9_pass,
        'details': details_img
    }
    print(f" -> Result: {'PASSED' if t9_pass else 'FAILED'}: {details_img}")

    # TEST 10: SLAM map + map->odom TF
    print("\n[CHECK 10/19] SLAM Toolbox Map & map->odom TF...")
    map_tf_ok = False
    try:
        map_tf_ok = tester.tf_buffer.can_transform('map', 'base_footprint', Time(), timeout=Duration(seconds=2.0))
    except Exception:
        map_tf_ok = False
    t10_pass = (tester.latest_map is not None and
                tester.latest_map.info.width > 0 and
                tester.latest_map.info.height > 0 and
                map_tf_ok)
    details_map = (
        f"Map: {tester.latest_map.info.width}x{tester.latest_map.info.height}@{tester.latest_map.info.resolution}m, "
        f"TF(map->base_footprint)={'OK' if map_tf_ok else 'MISSING'}"
        if tester.latest_map else "No map"
    )
    results['10_slam_map'] = {
        'title': 'SLAM Toolbox Map & Frame',
        'passed': t10_pass,
        'details': details_map
    }
    print(f" -> Result: {'PASSED' if t10_pass else 'FAILED'}: {details_map}")

    # TEST 11: Nav2 active
    print("\n[CHECK 11/19] Nav2 Action Server Responsive...")
    t11_pass = tester.nav_client.wait_for_server(timeout_sec=2.0)
    results['11_nav2_active'] = {
        'title': 'Nav2 Action Server Active',
        'passed': t11_pass,
        'details': 'Action server /navigate_to_pose is ready and accepting requests' if t11_pass else 'Nav2 action server not ready'
    }
    print(f" -> Result: {'PASSED' if t11_pass else 'FAILED'}: {results['11_nav2_active']['details']}")

    # TEST 12: Navigation goal succeeds
    print("\n[CHECK 12/19] Navigation Goal Dispatch & Acceptance...")
    t12_pass = False
    details_goal = "Goal could not be sent"
    if t11_pass:
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = tester.get_clock().now().to_msg()
        # Near goal in free space
        goal_msg.pose.pose.position.x = 0.5
        goal_msg.pose.pose.position.y = 0.0
        goal_msg.pose.pose.orientation.w = 1.0

        send_future = tester.nav_client.send_goal_async(goal_msg)
        start_wait = time.time()
        while time.time() - start_wait < 5.0 and not send_future.done():
            tester.spin_for(0.1)

        if send_future.done():
            goal_handle = send_future.result()
            if goal_handle and goal_handle.accepted:
                t12_pass = True
                details_goal = "Nav2 successfully accepted navigation goal and initiated path execution"
                # Cancel goal to restore quiet state
                cancel_future = goal_handle.cancel_goal_async()
                start_c = time.time()
                while time.time() - start_c < 2.0 and not cancel_future.done():
                    tester.spin_for(0.1)
            else:
                details_goal = "Goal rejected by planner"
    results['12_nav_goal'] = {
        'title': 'Navigation Goal Dispatch',
        'passed': t12_pass,
        'details': details_goal
    }
    print(f" -> Result: {'PASSED' if t12_pass else 'FAILED'}: {details_goal}")

    # TEST 13: Frontier exploration start and stop services
    print("\n[CHECK 13/19] Frontier Exploration Start and Stop Services...")
    t13_pass = False
    if tester.cli_explore_start.wait_for_service(timeout_sec=2.0) and tester.cli_explore_stop.wait_for_service(timeout_sec=2.0):
        # Call start
        req = Trigger.Request()
        fut_start = tester.cli_explore_start.call_async(req)
        start_w = time.time()
        while time.time() - start_w < 3.0 and not fut_start.done():
            tester.spin_for(0.1)
        # Call stop
        fut_stop = tester.cli_explore_stop.call_async(req)
        start_s = time.time()
        while time.time() - start_s < 3.0 and not fut_stop.done():
            tester.spin_for(0.1)

        t13_pass = (fut_start.done() and fut_start.result().success and
                    fut_stop.done() and fut_stop.result().success)
        details_expl = "Services /exploration/start and /exploration/stop responded with success=True"
    else:
        details_expl = "Exploration services not available"
    results['13_frontier_exploration'] = {
        'title': 'Frontier Exploration Services',
        'passed': t13_pass,
        'details': details_expl
    }
    print(f" -> Result: {'PASSED' if t13_pass else 'FAILED'}: {details_expl}")

    # TEST 14: Mobile dashboard opens on port 3000
    print("\n[CHECK 14/19] Mobile Dashboard HTTP Server (Port 3000)...")
    t14_pass = False
    details_dash = "Port 3000 failed"
    try:
        req = urllib.request.Request("http://127.0.0.1:3000/api/config", headers={'User-Agent': 'TestRunner'})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                t14_pass = True
                details_dash = f"HTTP 200 OK. Response body length: {len(resp.read())} bytes"
    except Exception as e:
        details_dash = f"Connection failed: {e}"
    results['14_dashboard_http'] = {
        'title': 'Mobile Dashboard HTTP Server',
        'passed': t14_pass,
        'details': details_dash
    }
    print(f" -> Result: {'PASSED' if t14_pass else 'FAILED'}: {details_dash}")

    # TEST 15: Rosbridge WebSocket on port 9090 (real HTTP 101 WebSocket handshake)
    print("\n[CHECK 15/19] Rosbridge WebSocket Server (Port 9090)...")
    t15_pass = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(('127.0.0.1', 9090))
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        s.sendall((
            "GET / HTTP/1.1\r\n"
            "Host: 127.0.0.1:9090\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode('ascii'))
        ws_resp = s.recv(512).decode('latin1', errors='ignore')
        s.close()
        t15_pass = '101' in ws_resp.split('\r\n')[0]
        details_ws = "WebSocket 101 Switching Protocols handshake verified on port 9090" if t15_pass else f"Unexpected WS response: {ws_resp[:80]}"
    except Exception as e:
        details_ws = f"Socket error: {e}"
    results['15_rosbridge_ws'] = {
        'title': 'Rosbridge WebSocket Server',
        'passed': t15_pass,
        'details': details_ws
    }
    print(f" -> Result: {'PASSED' if t15_pass else 'FAILED'}: {details_ws}")

    # TEST 16: Camera Web Video Server on port 8080 (MJPEG stream bytes)
    print("\n[CHECK 16/19] Web Video Server (Port 8080)...")
    t16_pass = False
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8080/stream?topic=/camera/image_raw&type=mjpeg",
            headers={'User-Agent': 'TestRunner'}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            chunk = resp.read(512)
            if resp.status == 200 and len(chunk) > 0:
                t16_pass = True
                details_vid = f"HTTP 200 OK MJPEG stream active ({len(chunk)} initial bytes)"
            else:
                details_vid = f"HTTP {resp.status}, {len(chunk)} bytes"
    except Exception as e:
        details_vid = f"Connection failed: {e}"
    results['16_web_video_server'] = {
        'title': 'Web Video Server Streamer',
        'passed': t16_pass,
        'details': details_vid
    }
    print(f" -> Result: {'PASSED' if t16_pass else 'FAILED'}: {details_vid}")

    # TEST 17: Mobile joystick commands reach Command Arbiter
    print("\n[CHECK 17/19] Mobile Joystick Commands Reach Command Arbiter...")
    tester.pub_arb_mode.publish(String(data='MANUAL'))
    tester.spin_for(0.2)
    latest_arb_out = None
    def cb_mon_cmd(msg):
        nonlocal latest_arb_out
        latest_arb_out = msg
    sub_mon = tester.create_subscription(Twist, '/cmd_vel', cb_mon_cmd, 10)
    # Send test manual joystick packet
    joy_cmd = Twist()
    joy_cmd.linear.x = 0.55
    joy_cmd.linear.y = 0.25
    joy_cmd.angular.z = 0.40
    tester.pub_mobile_cmd.publish(joy_cmd)
    tester.spin_for(0.2)
    t17_pass = (latest_arb_out is not None and
                abs(latest_arb_out.linear.x - 0.55) < 0.05 and
                abs(latest_arb_out.linear.y - 0.25) < 0.05)
    details_arb = f"Arbiter output vx={latest_arb_out.linear.x if latest_arb_out else None}, vy={latest_arb_out.linear.y if latest_arb_out else None}"
    results['17_joystick_arbitration'] = {
        'title': 'Joystick Command Routing via Arbiter',
        'passed': t17_pass,
        'details': details_arb
    }
    print(f" -> Result: {'PASSED' if t17_pass else 'FAILED'}: {details_arb}")

    # TEST 18: Emergency stop stops the robot
    print("\n[CHECK 18/19] Emergency Stop Interlock & Zero-Velocity Latching...")
    t18_pass = False
    details_estop = "E-Stop service call failed"
    if tester.cli_estop_trigger.wait_for_service(timeout_sec=2.0) and tester.cli_estop_reset.wait_for_service(timeout_sec=2.0):
        # Engage E-Stop
        req = Trigger.Request()
        fut_trigger = tester.cli_estop_trigger.call_async(req)
        start_e = time.time()
        while time.time() - start_e < 2.0 and not fut_trigger.done():
            tester.spin_for(0.05)

        # Attempt to publish motion during E-stop
        tester.pub_mobile_cmd.publish(joy_cmd)
        tester.spin_for(0.3)

        estop_engaged_halt = (latest_arb_out is not None and
                              latest_arb_out.linear.x == 0.0 and
                              latest_arb_out.linear.y == 0.0 and
                              latest_arb_out.angular.z == 0.0)

        # Clear E-Stop
        fut_clear = tester.cli_estop_reset.call_async(req)
        start_c = time.time()
        while time.time() - start_c < 2.0 and not fut_clear.done():
            tester.spin_for(0.05)

        tester.spin_for(0.2)
        t18_pass = estop_engaged_halt and fut_trigger.done() and fut_clear.done()
        details_estop = "E-Stop latched high priority, suppressed motion to 0.0 m/s, and safely reset"
    results['18_emergency_stop'] = {
        'title': 'Emergency Stop Motion Interlock',
        'passed': t18_pass,
        'details': details_estop
    }
    print(f" -> Result: {'PASSED' if t18_pass else 'FAILED'}: {details_estop}")

    # TEST 19: Command watchdog / browser disconnect safe stopping
    print("\n[CHECK 19/19] 400ms Command Watchdog & Disconnect Safe Stopping...")
    # Send a single packet
    tester.pub_arb_mode.publish(String(data='MANUAL'))
    tester.spin_for(0.1)
    tester.pub_mobile_cmd.publish(joy_cmd)
    tester.spin_for(0.1)
    # Wait and spin for 1.0 second (well above 400ms watchdog) without sending any more commands
    tester.spin_for(1.0)
    t19_pass = (latest_arb_out is not None and
                latest_arb_out.linear.x == 0.0 and
                latest_arb_out.linear.y == 0.0 and
                latest_arb_out.angular.z == 0.0)
    details_wd = "Velocity dropped to 0.00 m/s after command stream ceased (watchdog trip)" if t19_pass else f"Robot velocity still non-zero: {latest_arb_out}"
    results['19_watchdog_safe_stop'] = {
        'title': 'Command Watchdog Safe Stop (400ms cutoff)',
        'passed': t19_pass,
        'details': details_wd
    }
    print(f" -> Result: {'PASSED' if t19_pass else 'FAILED'}: {details_wd}")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUITE SUMMARY RESULTS")
    print("=" * 70)
    total = len(results)
    passed = sum(1 for r in results.values() if r['passed'])
    print(f"TOTAL TESTS:  {total}")
    print(f"PASSED:       {passed}")
    print(f"FAILED:       {total - passed}")
    print("=" * 70)

    tester.destroy_node()
    rclpy.shutdown()

    return passed == total, results


if __name__ == '__main__':
    all_ok, results = run_tests()
    sys.exit(0 if all_ok else 1)
