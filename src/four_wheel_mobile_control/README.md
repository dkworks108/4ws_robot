# Four-Wheel Mobile Control Package (`four_wheel_mobile_control`)

A professional, touch-optimized mobile web teleoperation and autonomous mission-monitoring dashboard for the **Project 04 Four-Wheel Steering Autonomous Mobile Robot**.

## Features

- **Mobile-First Responsive Dashboard:** Runs on Android, iPhone, iPad, tablets, and desktop workstations.
- **Central Command Arbiter:** Enforces strict single-authority ownership between manual driving, Nav2, and frontier exploration.
- **Dead-Man Switch & Watchdog:** 400 ms timeout stops the robot immediately if the joystick is released or the browser disconnects.
- **5 Steering Modes:** Front Ackermann, 4WS Counter-Phase, Crab, Generalized Swerve, and Rotation-In-Place.
- **Live RGB Camera Streaming:** Zero-overhead MJPEG streaming via `web_video_server`.
- **2D LiDAR Radar View:** Interactive canvas visualizer with distance rings and proximity color-coding.
- **SLAM Map & Click-to-Goal Navigation:** Real-time occupancy grid rendering with tap-to-navigate destination dispatch.
- **Autonomous Exploration Management:** Start, pause, resume, and stop exploration with live coverage percentage.

## Usage

Attach mobile control to a running simulation:
```bash
source /opt/ros/humble/setup.bash
source /media/bumble/DATA_DISK/robotics/opt/ros_extra/setup.bash
source /media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering/install/setup.bash

ros2 launch four_wheel_mobile_control mobile_control.launch.py
```

Open on mobile browser:
```
http://<ROBOT_IP>:3000
```

