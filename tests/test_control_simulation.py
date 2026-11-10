#!/usr/bin/env python3
"""
Gazebo Fortress Integration Test for Four-Wheel Steering Robot.

Validates in real-time headless simulation:
1. Clock synchronization (/clock)
2. Controller activation (joint_state_broadcaster, steering_controller, drive_controller)
3. Sensor stream publication (/joint_states, /odom, /imu/data, /scan)
4. Ground contact and physics stability (settling, negligible drift, zero roll/pitch)
5. Forward translation (Mode B)
6. Diagonal/lateral crab translation (Mode C)
7. Rotation-in-place (Mode E)
8. Braking stop
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
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, Imu, JointState
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String


def quaternion_to_euler(q):
    sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
    cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (q.w * q.y - q.z * q.x)
    pitch = math.asin(max(-1.0, min(1.0, sinp)))

    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


class SimulationTesterNode(Node):
    def __init__(self):
        super().__init__('simulation_tester_node')

        self.latest_clock = None
        self.latest_odom = None
        self.latest_scan = None
        self.latest_imu = None
        self.latest_joint_states = None

        self.create_subscription(Clock, '/clock', self.cb_clock, 10)
        self.create_subscription(Odometry, '/odom', self.cb_odom, 10)
        self.create_subscription(LaserScan, '/scan', self.cb_scan, 10)
        self.create_subscription(Imu, '/imu/data', self.cb_imu, 10)
        self.create_subscription(JointState, '/joint_states', self.cb_joint_states, 10)

        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_mode = self.create_publisher(String, '/four_wheel/set_mode', 10)

    def cb_clock(self, msg: Clock):
        self.latest_clock = msg

    def cb_odom(self, msg: Odometry):
        self.latest_odom = msg

    def cb_scan(self, msg: LaserScan):
        self.latest_scan = msg

    def cb_imu(self, msg: Imu):
        self.latest_imu = msg

    def cb_joint_states(self, msg: JointState):
        self.latest_joint_states = msg

    def spin_duration(self, seconds: float):
        start = time.time()
        while time.time() - start < seconds and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)


def run_simulation_tests():
    ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 70)
    print("STARTING GAZEBO FORTRESS INTEGRATION TESTS FOR 4WS ROBOT")
    print("=" * 70)

    # Clean up old processes
    subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher", "four_wheel_kinematics_node"],
                   stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    # Launch headless gazebo simulation
    launch_cmd = [
        "ros2", "launch", "four_wheel_description", "gazebo.launch.py",
        "headless:=true", "rviz:=false"
    ]
    proc = subprocess.Popen(launch_cmd, preexec_fn=os.setsid)

    rclpy.init()
    tester = SimulationTesterNode()

    results = {}
    try:
        # 1. Wait for clock
        print("[TEST 1/8] Waiting for Gazebo /clock...")
        clock_received = False
        t_start = time.time()
        while time.time() - t_start < 25.0:
            tester.spin_duration(0.2)
            if tester.latest_clock is not None:
                clock_received = True
                break

        assert clock_received, "Failed to receive /clock from Gazebo within 25s"
        sim_sec = tester.latest_clock.clock.sec
        print(f" -> PASS: /clock received! sim_time={sim_sec}s")
        results['clock'] = True

        # 2. Wait for controllers and sensor streams
        print("[TEST 2/8] Waiting for sensor topics (/joint_states, /odom, /imu/data, /scan)...")
        sensors_ready = False
        t_start = time.time()
        while time.time() - t_start < 20.0:
            tester.spin_duration(0.2)
            if (tester.latest_joint_states is not None and
                tester.latest_odom is not None and
                tester.latest_imu is not None and
                tester.latest_scan is not None):
                sensors_ready = True
                break

        assert sensors_ready, (
            f"Sensor timeout: joint_states={tester.latest_joint_states is not None}, "
            f"odom={tester.latest_odom is not None}, imu={tester.latest_imu is not None}, "
            f"scan={tester.latest_scan is not None}"
        )
        print(" -> PASS: All sensor topics active and streaming!")
        results['sensors'] = True

        # Allow controller spawners to fully activate
        tester.spin_duration(2.0)

        # 3. Ground contact and physics stability
        print("[TEST 3/8] Checking ground settling and physics stability...")
        tester.spin_duration(2.0)
        assert tester.latest_odom is not None
        p = tester.latest_odom.pose.pose.position
        q = tester.latest_odom.pose.pose.orientation
        roll, pitch, yaw = quaternion_to_euler(q)

        drift = math.hypot(p.x, p.y)
        print(f" -> Settled pose: pos=({p.x:.4f}, {p.y:.4f}), drift={drift:.4f}m, roll={math.degrees(roll):.2f}°, pitch={math.degrees(pitch):.2f}°")
        assert drift < 0.08, f"Robot drifted significantly during settling: {drift:.4f}m"
        assert abs(roll) < 0.1 and abs(pitch) < 0.1, f"Robot unstable on ground: roll={roll}, pitch={pitch}"
        print(" -> PASS: Physics stable, robot resting solidly on ground plane.")
        results['physics_stability'] = True

        # 4. Mode B: Forward translation
        print("[TEST 4/8] Testing forward translation in Mode B (4WS)...")
        tester.pub_mode.publish(String(data="four_wheel_steer"))
        start_x = tester.latest_odom.pose.pose.position.x
        start_y = tester.latest_odom.pose.pose.position.y

        twist = Twist()
        twist.linear.x = 0.40
        for _ in range(50):  # Drive for 2.5s
            tester.pub_cmd_vel.publish(twist)
            tester.spin_duration(0.05)

        end_x = tester.latest_odom.pose.pose.position.x
        end_y = tester.latest_odom.pose.pose.position.y
        disp_x = end_x - start_x
        print(f" -> Forward displacement: dx={disp_x:.3f}m (target >= 0.40m)")
        assert disp_x >= 0.35, f"Forward displacement insufficient: {disp_x:.3f}m"
        print(" -> PASS: Forward translation verified!")
        results['forward_translation'] = True

        # Stop
        stop_cmd = Twist()
        for _ in range(15):
            tester.pub_cmd_vel.publish(stop_cmd)
            tester.spin_duration(0.05)

        # 5. Mode C: Crab translation (diagonal / lateral)
        print("[TEST 5/8] Testing crab steering mode (pure lateral translation vy)...")
        tester.pub_mode.publish(String(data="crab"))
        tester.spin_duration(0.5)

        start_x = tester.latest_odom.pose.pose.position.x
        start_y = tester.latest_odom.pose.pose.position.y

        crab_twist = Twist()
        crab_twist.linear.x = 0.0
        crab_twist.linear.y = 0.35
        for _ in range(50):  # Drive laterally for 2.5s
            tester.pub_cmd_vel.publish(crab_twist)
            tester.spin_duration(0.05)

        end_x = tester.latest_odom.pose.pose.position.x
        end_y = tester.latest_odom.pose.pose.position.y
        disp_y = end_y - start_y
        print(f" -> Crab lateral displacement: dy={disp_y:.3f}m (target >= 0.25m)")
        assert abs(disp_y) >= 0.25, f"Crab displacement insufficient: {disp_y:.3f}m"
        print(" -> PASS: Crab translation verified!")
        results['crab_translation'] = True

        # Stop
        for _ in range(15):
            tester.pub_cmd_vel.publish(stop_cmd)
            tester.spin_duration(0.05)

        # 6. Mode E: Rotation-In-Place
        print("[TEST 6/8] Testing Mode E: Rotation-in-place (pure yaw spin)...")
        tester.pub_mode.publish(String(data="in_place_spin"))
        tester.spin_duration(0.5)

        start_q = tester.latest_odom.pose.pose.orientation
        _, _, start_yaw = quaternion_to_euler(start_q)
        spin_start_x = tester.latest_odom.pose.pose.position.x
        spin_start_y = tester.latest_odom.pose.pose.position.y

        spin_twist = Twist()
        spin_twist.angular.z = 0.80
        for _ in range(50):  # Spin for 2.5s
            tester.pub_cmd_vel.publish(spin_twist)
            tester.spin_duration(0.05)

        end_q = tester.latest_odom.pose.pose.orientation
        _, _, end_yaw = quaternion_to_euler(end_q)
        spin_end_x = tester.latest_odom.pose.pose.position.x
        spin_end_y = tester.latest_odom.pose.pose.position.y

        delta_yaw = end_yaw - start_yaw
        # Unwind angle difference
        delta_yaw = math.atan2(math.sin(delta_yaw), math.cos(delta_yaw))
        trans_slip = math.hypot(spin_end_x - spin_start_x, spin_end_y - spin_start_y)

        print(f" -> In-place rotation: delta_yaw={math.degrees(delta_yaw):.1f}° ({delta_yaw:.3f} rad), center translation drift={trans_slip:.3f}m")
        assert abs(delta_yaw) >= 0.60, f"Yaw rotation insufficient: {delta_yaw:.3f} rad"
        assert trans_slip < 0.20, f"Translational drift during in-place spin too high: {trans_slip:.3f}m"
        print(" -> PASS: Pure in-place rotation verified!")
        results['in_place_spin'] = True

        # 7. Safe stop braking
        print("[TEST 7/8] Testing braking and safe stop...")
        for _ in range(20):
            tester.pub_cmd_vel.publish(stop_cmd)
            tester.spin_duration(0.05)

        tester.spin_duration(1.0)
        final_vx = tester.latest_odom.twist.twist.linear.x
        final_vy = tester.latest_odom.twist.twist.linear.y
        final_wz = tester.latest_odom.twist.twist.angular.z
        residual_speed = math.hypot(final_vx, final_vy)
        print(f" -> Residual speed after braking: {residual_speed:.5f} m/s, wz={final_wz:.5f} rad/s")
        assert residual_speed < 0.05, f"Residual speed too high: {residual_speed}"
        print(" -> PASS: Complete standstill achieved!")
        results['braking_stop'] = True

        # 8. Sensor data sanity check
        print("[TEST 8/8] Validating LiDAR scan and IMU readings...")
        scan = tester.latest_scan
        valid_ranges = [r for r in scan.ranges if scan.range_min <= r <= scan.range_max]
        min_range = min(valid_ranges) if valid_ranges else 0.0
        print(f" -> LiDAR scan: {len(scan.ranges)} samples, {len(valid_ranges)} valid returns, min_range={min_range:.3f}m")
        assert len(scan.ranges) == 720, f"Expected 720 samples, got {len(scan.ranges)}"
        assert min_range > 0.30, f"Chassis self-scanning detected! min_range={min_range:.3f}m (should be > 0.30m)"
        assert len(valid_ranges) > 50, f"Insufficient valid returns: {len(valid_ranges)}"

        imu = tester.latest_imu
        accel_z = imu.linear_acceleration.z
        print(f" -> IMU linear acceleration z: {accel_z:.2f} m/s^2 (gravity reference ~9.8)")
        assert 7.0 <= accel_z <= 12.0, f"Abnormal IMU gravity: {accel_z}"
        print(" -> PASS: Sensors verified completely!")
        results['sensors_sanity'] = True

    finally:
        tester.destroy_node()
        rclpy.shutdown()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher", "four_wheel_kinematics_node"],
                       stderr=subprocess.DEVNULL)
        time.sleep(1.0)

    print("=" * 70)
    print("GAZEBO FORTRESS SIMULATION TEST SUMMARY:")
    all_passed = all(results.values()) and len(results) == 8
    for name, passed in results.items():
        print(f"  - {name:25s}: {'[PASS]' if passed else '[FAIL]'}")
    print(f"OVERALL RESULT: {'ALL 8 TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 70)
    return all_passed


if __name__ == '__main__':
    success = run_simulation_tests()
    sys.exit(0 if success else 1)
