# Four-Wheel Steering Autonomous Mobile Robot — Robot Architecture

## 1. System Overview

The **Four-Wheel Steering (4WS / 4WD) Mobile Robot** is an advanced robotic locomotion platform developed for high-agility navigation in constrained indoor environments. Unlike conventional two-wheel differential drive robots or fixed-axle four-wheel skid-steer systems, this robot features **four independently steered knuckles** paired with **four independently driven continuous traction wheels** (total 8 active actuated degrees of freedom).

This architecture eliminates tire scrubbing, maximizes traction efficiency, and permits five distinct locomotion and steering modes ranging from classical Ackermann car-like steering to zero-radius rotation in place and omnidirectional crab motion.

```
       Front Axle (+X)
    [FL Wheel]     [FR Wheel]
       \  /           \  /
        ===[Chassis]===
       /  \           /  \
    [RL Wheel]     [RR Wheel]
        Rear Axle (-X)
```

---

## 2. Physical & Mechanical Parameters

| Parameter | Symbol | Value | Units | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Wheelbase** | $L$ | `0.360` | m | Distance between front and rear steering knuckle axes |
| **Track Width** | $W$ | `0.360` | m | Distance between left and right steering knuckle axes |
| **Wheel Radius** | $r$ | `0.080` | m | High-traction rubber simulated tire |
| **Wheel Width** | $b_w$ | `0.040` | m | Lateral contact patch thickness |
| **Chassis Dimensions** | $(L_c, W_c, H_c)$ | `0.45 x 0.32 x 0.12` | m | Aluminum rectangular monocoque frame |
| **Chassis Mass** | $m_c$ | `12.0` | kg | Primary body structure containing avionics |
| **Knuckle Mass** | $m_k$ | `0.5` | kg each ($x4 = 2.0$ kg) | Steering pivot knuckle |
| **Wheel Mass** | $m_w$ | `0.6` | kg each ($x4 = 2.4$ kg) | Wheel rim and tire assembly |
| **LiDAR + Sensors** | $m_s$ | `0.1` | kg | GPU LiDAR + IMU + Camera |
| **Total Mass** | $M_{total}$ | `16.502` | kg | Verified non-zero positive mass for all links |
| **Ground Clearance** | $h_{gc}$ | `0.040` | m | Clearance between chassis bottom and plane |
| **Steering Joint Limit** | $\delta_{max}$ | `±1.5708` | rad | $\pm 90^\circ$ maximum steering knuckle deflection |
| **Maximum Linear Velocity** | $v_{max}$ | `1.50` | m/s | Safe simulation velocity ceiling |
| **Maximum Angular Velocity** | $\omega_{max}$ | `2.50` | rad/s | Maximum yaw rate |

---

## 3. Modular URDF / Xacro Description Architecture

The kinematic and visual robot description is factored into modular Xacro sub-files located in `src/four_wheel_description/urdf/`:

```
src/four_wheel_description/urdf/
├── robot.urdf.xacro          # Master entry point uniting all subsystems
├── materials.xacro           # Color definitions and visual material tokens
├── chassis.xacro             # Main monocoque body, base_footprint, and base_link
├── steering.xacro            # Macro for revolute steering knuckle links and joints
├── wheel.xacro               # Macro for continuous wheel links and traction joints
├── sensors.xacro             # GPU LiDAR, 6-DoF IMU, and RGB camera integration
└── ros2_control.xacro        # Hardware interface tags for ign_ros2_control plugin
```

### 3.1 Kinematic Joint Hierarchy

```
base_footprint (Root Link, Z=0 ground projection)
 └── base_link (Chassis Origin, Z=0.08m)
      ├── fl_knuckle_link (fl_steering_joint, Revolute, Z-axis)
      │    └── fl_wheel_link (fl_wheel_joint, Continuous, Y-axis)
      ├── fr_knuckle_link (fr_steering_joint, Revolute, Z-axis)
      │    └── fr_wheel_link (fr_wheel_joint, Continuous, Y-axis)
      ├── rl_knuckle_link (rl_steering_joint, Revolute, Z-axis)
      │    └── rl_wheel_link (rl_wheel_joint, Continuous, Y-axis)
      ├── rr_knuckle_link (rr_steering_joint, Revolute, Z-axis)
      │    └── rr_wheel_link (rr_wheel_joint, Continuous, Y-axis)
      ├── lidar_link (laser_joint, Fixed, Z=+0.11m on top plate)
      ├── imu_link (imu_joint, Fixed, geometric center)
      └── camera_link (camera_joint, Fixed, forward facing +X)
           └── camera_optical_link (camera_optical_joint, Fixed, standard optical frame)
```

---

## 4. Sensor Suite Specifications

### 4.1 2D GPU LiDAR
- **Link Frame:** `lidar_link`
- **Ignition Sensor Type:** `gpu_lidar`
- **Fortress Frame Binding:** `<gz_frame_id>lidar_link</gz_frame_id>`
- **Samples:** `720` rays over full $360^\circ$ ($2\pi$ radians)
- **Range:** $0.10$ m minimum to $12.0$ m maximum
- **Update Frequency:** $10$ Hz
- **ROS 2 Topic:** `/scan` (`sensor_msgs/msg/LaserScan`)
- **Mounting Position:** Elevated to $Z = +0.19$ m from ground to eliminate self-scanning of the wheels or chassis.

### 4.2 Inertial Measurement Unit (IMU)
- **Link Frame:** `imu_link`
- **Ignition Sensor Type:** `imu`
- **Fortress Frame Binding:** `<gz_frame_id>imu_link</gz_frame_id>`
- **Update Frequency:** $50$ Hz
- **ROS 2 Topic:** `/imu/data` (`sensor_msgs/msg/Imu`)
- **Noise Characteristics:** Gaussian noise model on angular rates ($0.0002$ rad/s) and linear accelerations ($0.001$ m/s²).

### 4.3 Forward RGB Camera
- **Link Frame:** `camera_link` (Optical: `camera_optical_link`)
- **Resolution:** $640 \times 480$ pixels at $30$ FPS
- **Field of View:** $1.047$ rad ($60^\circ$)
- **ROS 2 Topic:** `/camera/image_raw` (`sensor_msgs/msg/Image`)

---

## 5. TF2 Transform Tree Integrity

The coordinate transform pipeline follows the strict ROS REP-105 standard:

$$\text{map} \xrightarrow{\text{SLAM Toolbox}} \text{odom} \xrightarrow{\text{Kinematics Odometry}} \text{base\_footprint} \xrightarrow{\text{URDF Fixed}} \text{base\_link} \xrightarrow{\text{URDF}} \text{Sensors \& Knuckles}$$

1. `map` $\to$ `odom`: Broadcasted dynamically by `async_slam_toolbox_node` at $20$ Hz, correcting dead-reckoning odometry drift via scan-matching against the global map.
2. `odom` $\to$ `base_footprint`: Broadcasted at $50$ Hz by `four_wheel_kinematics_node`, integrating planar forward kinematics from actual wheel velocity feedback and knuckle steering positions.
3. `base_footprint` $\to$ `base_link`: Broadcasted by `robot_state_publisher` from URDF (rigid elevation $Z = 0.08$ m).
4. `base_link` $\to$ sensor/wheel frames: Broadcasted continuously by `robot_state_publisher` using joint states received from `joint_state_broadcaster`.
