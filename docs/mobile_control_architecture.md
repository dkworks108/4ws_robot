# Mobile Control System Architecture
## 4ws_robot — Four-Wheel Steering Autonomous Mobile Robot

### 1. Architectural Overview

The **Four-Wheel Mobile Control System** (`four_wheel_mobile_control`) provides a modern, touch-optimized, mobile-first web teleoperation and autonomous mission-monitoring stack for the 4WS/4WD autonomous ground vehicle.

The system connects browser runtimes (Android phones, iPhones, iPads, Android tablets, and desktop workstations) to the underlying ROS 2 Humble robotics stack via high-throughput WebSockets and HTTP video streaming.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CLIENT LAYER (Browser Runtime)                       │
│  React 18 + Vite + TypeScript + Tailwind CSS (Responsive Mobile UI)    │
│  ┌────────────────────┬──────────────────────┬──────────────────────┐  │
│  │ Virtual Joystick   │ 5 Steering Selectors │ Safety E-Stop Button │  │
│  ├────────────────────┼──────────────────────┼──────────────────────┤  │
│  │ Live 2D LiDAR Radar│ SLAM Occupancy Map   │ Live RGB MJPEG Feed  │  │
│  └────────────────────┴──────────────────────┴──────────────────────┘  │
└───────────────────▲──────────────────────────────▲─────────────────────┘
                    │ WebSocket (JSON / CBOR)      │ HTTP MJPEG (Port 8080)
                    │ (Port 9090)                  │
┌───────────────────▼──────────────────────────────▼─────────────────────┐
│                 COMMUNICATION & ARBITRATION BRIDGE                      │
│                                                                        │
│   [rosbridge_websocket]      [rosapi]         [web_video_server]       │
│             │                   │                      │               │
│             ▼                   ▼                      ▼               │
│   ┌──────────────────────────────────────────────────────────────┐     │
│   │            Command Arbiter & Safety Multiplexer              │     │
│   │   (single authority, dead-man timeout, speed limit scale)    │     │
│   └───────▲─────────────────────▲────────────────────────┬───────┘     │
└───────────┼─────────────────────┼────────────────────────┼─────────────┘
            │ /mobile/cmd_vel     │ /cmd_vel_nav           │ /cmd_vel
            │ (Manual Joystick)   │ (Nav2 / Explorer)      │ (Safe Multi)
┌───────────┴─────────────────────┴────────────────────────▼─────────────┐
│                      CORE ROBOTICS SUBSYSTEM                           │
│                                                                        │
│   [four_wheel_kinematics_node] ◄── 8-DOF Kinematics & Odometry         │
│   [Nav2 Navigation Stack]      ◄── NavigateToPose & Costmaps           │
│   [SLAM Toolbox Online Async]  ◄── 20m Scan Matching & Map Building    │
│   [Frontier Explorer Node]     ◄── Full-Map Autonomous Coverage        │
│   [Gazebo Fortress / Hardware] ◄── ros2_control Joint Actuators        │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Package Responsibilities

| Component | Package / Module | Responsibility |
| :--- | :--- | :--- |
| **Frontend UI** | `four_wheel_mobile_control/frontend` | Single Page Application (SPA) offering virtual joystick, mode selection, radar, SLAM map, camera, and telemetry. |
| **Web Server Node** | `four_wheel_mobile_control/web_server.py` | Embedded multi-threaded HTTP server serving production static assets on port 3000 and LAN IP discovery. |
| **Command Arbiter** | `four_wheel_mobile_control/command_arbiter_node.py` | Single movement authority enforcement, dead-man watchdog timer, mode transitions, and emergency stop latching. |
| **Rosbridge Suite** | `rosbridge_server` / `rosbridge_websocket` | High-throughput bi-directional JSON/WebSocket bridge between browser clients and ROS 2 middleware. |
| **Web Video Server**| `web_video_server` | Converts ROS 2 `sensor_msgs/Image` to MJPEG streams for zero-dependency browser video delivery. |
| **Kinematics Engine**| `four_wheel_control` | Computes 4-knuckle steering angles and 4-wheel drive speeds across 5 distinct kinematic modes. |

---

### 3. Dataflow & Communication Interfaces

1. **Manual Driving Flow:**
   - Touch Virtual Joystick &rarr; normalized $(v_x, v_y, \omega_z)$ &rarr; WebSocket &rarr; `rosbridge_websocket` &rarr; `/mobile/cmd_vel` (`geometry_msgs/Twist`) &rarr; `command_arbiter_node` (applies speed limit & watchdog check) &rarr; `/cmd_vel` &rarr; `four_wheel_kinematics_node` &rarr; `ros2_control` hardware interfaces.

2. **Sensor Feedback Flow:**
   - Gazebo Fortress Camera &rarr; `/camera/image_raw` &rarr; `web_video_server` &rarr; HTTP MJPEG Stream &rarr; Browser `<img>` element.
   - Gazebo 20m LiDAR &rarr; `/scan` &rarr; `rosbridge` &rarr; HTML5 Canvas 2D Radar with proximity danger color grading.
   - SLAM Toolbox &rarr; `/map` &rarr; `rosbridge` &rarr; Interactive Pan/Zoom Canvas with robot footprint, heading arrow, and Nav2 global path.

