# Visual Documentation Gallery

This gallery catalogs verified visual outputs captured from Project 04 across Gazebo Fortress simulation, PyBullet geometry checks, RViz2 sensor visualization, SLAM Toolbox mapping, Nav2 navigation, autonomous frontier exploration, and the pixel-art Desktop + Mobile ground-control dashboard.

---

## 1. Ground-Control Dashboard (Desktop, Tablet, and Mobile UI)

### 1.1 Desktop Ground-Control Station (`1440x900`)

![Desktop Ground-Control Station](../screenshots/mobile_dashboard_desktop.png)

**Demonstrates:** Live desktop workstation layout running against Gazebo Fortress over `rosbridge_websocket` (`:9090`) and `web_video_server` (`:8080`). Displays header telemetry (`CONNECTED`, `GAZEBO (SIM)`, FPS, latency), left section navigation rail, sticky `SYSTEM SAFETY INTERLOCK` (`ARMED & READY`, `EMERGENCY STOP`), `CONTROL AUTHORITY` (`MANUAL` / `NAV2` / `EXPLORE`), five 4WS steering modes (`D. SWERVE` active), speed limit bar, manual joystick + desktop keyboard indicator (`W/A/S/D/Q/E/Space`), top-down wheel steering angle visualizer, live RGB camera stream, 360-degree LiDAR polar scan, and IMU orientation view.

### 1.2 Mobile One-Handed Pilot Interface — Right-Handed (`412x915`)

![Mobile Pilot Right-Handed](../screenshots/mobile_dashboard_phone.png)

**Demonstrates:** Mobile phone layout with right-thumb placement for the omnidirectional joystick and `CCW` / `CW` rotation controls, left-aligned Top-Down Robot View, collapsible sensor jump rows (`LiDAR`, `IMU`, `MAP`), live odometry/watchdog strip, sticky E-Stop interlock, and sticky bottom tabs (`PILOT`, `MAP`, `SENSORS`, `TELEMETRY`).

### 1.3 Mobile One-Handed Pilot Interface — Left-Handed (`412x915`)

![Mobile Pilot Left-Handed](../screenshots/mobile_dashboard_phone_lefthanded.png)

**Demonstrates:** Left-handed mobile configuration toggled from the Settings modal, mirroring the joystick and `CCW`/`CW` rotation buttons to the left side and moving the Top-Down Robot View (showing diagonal swerve wheel deflections) to the right.

### 1.4 Tablet Responsive Layout (`768x1024`)

![Tablet Ground-Control Interface](../screenshots/mobile_dashboard_tablet.png)

**Demonstrates:** Responsive tablet presentation preserving single-column safety banner hierarchy, full status badges, touchscreen joystick, live camera feed, and sticky tab bar without horizontal overflow.

---

## 2. Gazebo Simulation and RViz2 Visualization

| Gazebo Fortress Arena Spawn | RViz2 Live Sensor & TF Model |
| :---: | :---: |
| ![Gazebo Robot](../screenshots/gazebo_robot.png) | ![RViz2 Model](../screenshots/rviz_model.png) |

| RViz2 Front View | RViz2 Side View | RViz2 Top View |
| :---: | :---: | :---: |
| ![RViz Front](../screenshots/rviz_front.png) | ![RViz Side](../screenshots/rviz_side.png) | ![RViz Top](../screenshots/rviz_top.png) |

**Demonstrates:** Eight actuated joints rendered in Ignition Gazebo Fortress alongside RViz2 TF frames, URDF link geometry, 720-beam LiDAR scan overlay, and IMU/odometry frame transforms (`map -> odom -> base_footprint -> base_link`).

---

## 3. Robot 3D Geometry and 4WS Steering Configurations

| Steering Modes Overview | Isometric 3D Model |
| :---: | :---: |
| ![Steering Modes Diagram](../screenshots/steering_modes.png) | ![Robot Isometric 3D](../screenshots/robot_isometric_3d.png) |

| Mode B: Counter-Phase 4WS | Mode C: Crab Parallel | Mode E: Rotation-In-Place |
| :---: | :---: | :---: |
| ![Counter-Phase 4WS](../screenshots/robot_steering_counterphase.png) | ![Crab Steering](../screenshots/robot_steering_crab.png) | ![In-Place Spin](../screenshots/robot_steering_inplace.png) |

**Demonstrates:** Physical wheel-knuckle geometry across Ackermann, symmetric counter-phase 4WS (`+25/-25 deg`), parallel crab translation (`+35 deg` all corners), and tangential rotation-in-place (`+/-45 deg`).

---

## 4. SLAM Mapping, Nav2 Path Planning, and Autonomous Exploration

| SLAM Toolbox Occupancy Grid | Nav2 Planned Trajectory | Frontier-Based Autonomous Exploration |
| :---: | :---: | :---: |
| ![SLAM Map](../screenshots/slam_map.png) | ![Nav2 Path](../screenshots/nav2_path.png) | ![Autonomous Exploration](../screenshots/autonomous_exploration.png) |

**Demonstrates:** Online asynchronous `slam_toolbox` 5 cm occupancy grid generation (`odom -> map` loop closure), Nav2 DWB/Navfn path execution around obstacles, and frontier clustering/goal selection during automated arena mapping.
