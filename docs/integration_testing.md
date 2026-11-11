# Project 04 — Integration & Verification Testing Guide

## 1. Test Architecture

Verification is separated into discrete test layers rather than one opaque script:

| Layer | File | Requires Live Gazebo? | Coverage |
|---|---|---|---|
| A. Static Checks | `tests/test_static_checks.py` | No | XML, Xacro/URDF, SDF Fortress checks, YAML, Python syntax, package discovery, launch parsing, frontend build |
| B. Unit Tests | `tests/test_kinematics.py`, `tests/test_urdf.py`, `tests/test_exploration.py`, `tests/test_mobile_control_suite.py` | No | 5 steering modes IK/FK, URDF tree/inertias, frontier detection/blacklisting, arbiter routing, monotonic watchdog, E-Stop |
| C–H. Live E2E Acceptance Suite | `tests/test_master_launch_e2e.py` | Yes (`complete_mobile_simulation.launch.py`) | Gazebo clock, 8 joints, 9 active controllers, 5 modes physical motion + odom, LiDAR/IMU/Camera+CameraInfo, SLAM `/map`+TF, Nav2 lifecycle & goal, Explorer services, HTTP/WS 101/MJPEG, Arbiter/E-Stop/Watchdog |
| Control/SLAM Sub-suites | `tests/test_control_simulation.py`, `tests/test_slam_navigation.py` | Yes | Targeted Gazebo control & SLAM/Nav2 checks |

---

## 2. Running Static & Unit Tests (Offline)

```bash
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
source /media/bumble/DATA_DISK/robotics/opt/ros_extra/setup.bash
cd /media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering
source install/setup.bash

/usr/bin/python3 -m pytest -v \
  tests/test_static_checks.py \
  tests/test_kinematics.py \
  tests/test_urdf.py \
  tests/test_exploration.py \
  tests/test_mobile_control_suite.py
```

---

## 3. Running Live Integrated E2E Tests

1. Start the full integrated system in Terminal 1:
   ```bash
   ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py headless:=true use_rviz:=false
   ```
2. Wait until `PROJECT 04 SYSTEM READY` is displayed (or `/system/system_ready` publishes `true`).
3. Run the 19-point E2E verification suite in Terminal 2:
   ```bash
   /usr/bin/python3 tests/test_master_launch_e2e.py
   ```
4. Verify map saving:
   ```bash
   ros2 run nav2_map_server map_saver_cli \
     -t /map -f maps/integrated_test_map \
     --ros-args -p map_subscribe_transient_local:=true -p use_sim_time:=true
   ```

