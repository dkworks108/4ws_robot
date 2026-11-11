# `four_wheel_description`

URDF/Xacro mechanical description, sensor modeling, RViz2 configuration, SDF simulation worlds, and Ignition Gazebo Fortress bringup for the Project 04 Four-Wheel Steering (`4WS/4WD`) robot.

---

## 1. Purpose

This package defines the robot's physical geometry, inertial tensors, steering knuckles, traction wheels, onboard sensors, `ign_ros2_control` plugin bindings, and simulation environments used by all downstream control, navigation, and dashboard packages.

---

## 2. Architecture and Key Components

| Component | Path | Responsibility |
| :--- | :--- | :--- |
| Top-level Xacro | `urdf/robot.urdf.xacro` | Assembles chassis, 4 steering knuckles, 4 wheels, sensors, and `ros2_control` bindings |
| Chassis Xacro | `urdf/chassis.xacro` | `base_footprint` -> `base_link` (`0.50 x 0.30 x 0.10 m`, `8.0 kg`) |
| Steering Macro | `urdf/steering.xacro` | Revolute steering knuckle joints (`fl`, `fr`, `rl`, `rr_steering_joint`) |
| Wheel Macro | `urdf/wheel.xacro` | Continuous wheel drive joints (`fl`, `fr`, `rl`, `rr_wheel_joint`, `r = 0.08 m`, `w = 0.04 m`, `0.6 kg`) |
| Sensors Xacro | `urdf/sensors.xacro` | 360-degree GPU LiDAR (`720` samples, `0.10-20.0 m`, `15 Hz`), IMU (`50 Hz`), RGB camera (`640x480` default, `15 Hz`) |
| Control Hardware Xacro | `urdf/ros2_control.xacro` | Declares Ignition Gazebo Fortress `ign_ros2_control` state and command interfaces for all 8 joints |
| Simulation Worlds | `worlds/outdoor_proving_ground.sdf`, `worlds/four_wheel_arena.sdf` | Gazebo Fortress SDF test environments |
| Simulation Launch | `launch/gazebo.launch.py`, `launch/complete_simulation.launch.py` | Launches Gazebo, spawns robot entity, bridges `/clock`, `/scan`, `/imu/data`, `/camera/*`, and spawns all 9 controllers |

### Physical Dimensions

- **Wheelbase:** `0.36 m` (`wheel_base_half = 0.18 m`)
- **Track Width:** `0.36 m` (`track_width_half = 0.18 m`)
- **Wheel Radius / Width:** `0.08 m` / `0.04 m`
- **Actuated Degrees of Freedom:** 8 joints (4 steering position joints + 4 wheel velocity joints)

---

## 3. Dependencies

- `ament_cmake`
- `robot_state_publisher`, `joint_state_publisher`, `xacro`, `rviz2`
- `ros_gz_sim`, `ros_gz_bridge`, `ign_ros2_control`

---

## 4. Build and Execution

Build standalone or as part of the workspace:

```bash
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
colcon build --packages-select four_wheel_description
source install/setup.bash
```

Launch Gazebo Fortress simulation with `ros2_control` and kinematics:

```bash
ros2 launch four_wheel_description gazebo.launch.py
```

Note: For the complete integrated system including command arbitration and web control, use `ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py`.

---

## 5. Configuration and Topics

| Launch / Xacro Parameter | Default | Description |
| :--- | :--- | :--- |
| `world` | `outdoor_proving_ground.sdf` | SDF world file path |
| `camera_width` | `640` | RGB camera horizontal resolution (px) |
| `camera_height` | `480` | RGB camera vertical resolution (px) |
| `controllers_yaml` | Package controller YAML | `ros2_control` controller configuration |

**Bridged Sensor Topics:** `/clock` (`rosgraph_msgs/Clock`), `/scan` (`sensor_msgs/LaserScan`), `/imu/data` (`sensor_msgs/Imu`), `/camera/image_raw` (`sensor_msgs/Image`), `/camera/camera_info` (`sensor_msgs/CameraInfo`).

---

## 6. Testing

```bash
/usr/bin/python3 -m pytest -v tests/test_urdf.py tests/test_static_checks.py
```

- `tests/test_urdf.py`: Validates Xacro expansion, single root link, 8 steering/wheel joints, sensor frames, and positive mass/inertia matrices (`TESTED`).
- `tests/test_static_checks.py`: Validates SDF XML compatibility with Gazebo Fortress (`TESTED`).

---

## 7. Known Limitations

- The legacy `launch/complete_simulation.launch.py` entry point launches autonomy directly without `command_arbiter_node` safety multiplexing; prefer `four_wheel_mobile_control/launch/complete_mobile_simulation.launch.py`.
- Collision and inertia parameters target simulated flat terrain (`outdoor_proving_ground.sdf`, `four_wheel_arena.sdf`) and require physical hardware calibration before deploying on a real rover.

