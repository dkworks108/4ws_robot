# `four_wheel_mobile_control`

Master launch orchestrator, safety command arbiter, runtime readiness monitor, local web server, and pixel-art React + TypeScript + Vite desktop/mobile ground-control interface for `4ws_robot`.

> [!WARNING]
> **DUBANT BETA NOTICE:** `4ws_robot` currently pairs with an external **Dubant** control/server system in **BETA** development. No Dubant server adapter binaries, private URLs, or credentials are included in this package; current browser teleoperation runs locally via HTTP (`:3000`), `rosbridge_websocket` (`:9090`), and `web_video_server` (`:8080`). See [`docs/dubant_beta_integration.md`](../../docs/dubant_beta_integration.md).

---

## Overview

`four_wheel_mobile_control` integrates all lower-level `4ws_robot` ROS 2 packages under a single readiness-gated startup workflow while providing deterministic multi-source velocity arbitration and responsive browser interfaces for desktop workstations and mobile phones.

## Purpose

1. Prevent multi-source motion collisions between manual joystick/keyboard input, Nav2, and frontier exploration via `command_arbiter_node`.
2. Gate multi-stage system bringup via `launch_gate` (`sim` -> `slam` -> `nav2`) and continuously monitor health via `system_readiness_node`.
3. Deliver a functional pixel-art ground-control dashboard (`frontend/`) over local Wi-Fi or localhost (`web_server`, `rosbridge_websocket`, `web_video_server`).

## Features

- **Single-Command Orchestration (`complete_mobile_simulation.launch.py`):** Pre-validates Fortress SDF worlds and gates Gazebo, SLAM, Nav2, Exploration, and Mobile Control startup. (`TESTED`)
- **Deterministic Command Arbiter (`command_arbiter_node`):** `50 Hz` exclusive authority gate (`MANUAL`, `AUTONOMOUS_NAV`, `AUTONOMOUS_EXPLORE`, `ESTOP`), `0.40 s` monotonic watchdog, `1.20 s` heartbeat watchdog, `0.15 s` mode-transition zero-hold lockout, speed scaling (`0.1-1.0`), and active goal/exploration cancellation on E-Stop. (`TESTED`)
- **Pixel-Art Desktop & Mobile UI (`frontend/`):** Responsive React + TypeScript dashboard (`#0F0F23` canvas, `#FF0000` / `#00FF00` / `#0000FF` / `#FFFF00` indicators, `Press Start 2P` + `JetBrains Mono`) with Web Audio 8-bit sound effects (`soundEffects.ts`) and mute persistence. (`TESTED`)
- **Unified Manual Input Pipeline (`manualInputPipeline.ts`):** Routes Desktop Keyboard (`W/A/S/D/Q/E`, `Space` immediate stop, diagonal combos, `ON/OFF` toggle), Desktop Mouse Joystick, and Mobile Touch Joystick through one safety-gated `/mobile/cmd_vel` publisher (`10 Hz`) that clears on E-Stop, authority change, `blur`, `visibilitychange`, and disconnect. (`TESTED`)
- **One-Handed Mobile Layout:** `PILOT`, `MAP`, `SENSORS`, `TELEMETRY` bottom tabs, persistent top E-Stop banner, and Left-Handed / Right-Handed control mirroring. (`TESTED`)
- **LAN HTTP Server & Readiness Monitor:** `web_server` (`0.0.0.0:3000`, `/api/health`, `/api/config`), `system_readiness_node` (`/system/system_ready`, `/system/readiness_status`). (`TESTED`)

## Architecture

```mermaid
flowchart TB
    UI["React + Vite Dashboard\n(Desktop Keyboard/Mouse & Mobile Touch)"]
    WebSrv["web_server (:3000)\nDist + /api/health + /api/config"]
    Video["web_video_server (:8080)\nMJPEG /camera/image_raw"]
    Bridge["rosbridge_websocket (:9090)"]

    UI <-->|"HTTP"| WebSrv
    UI <--|"MJPEG"| Video
    UI <-->|"WebSocket JSON"| Bridge

    Bridge -->|"/mobile/cmd_vel, /mobile/estop,\n/mobile/set_mode, /goal_pose"| Arbiter["command_arbiter_node (50 Hz)"]
    Nav2["Nav2 (/cmd_vel_nav)"] --> Arbiter
    Arbiter -->|"/cmd_vel"| Kin["four_wheel_kinematics_node"]
    Ready["system_readiness_node"] -->|"/system/readiness_status"| Bridge
```

## Directory Structure

```text
four_wheel_mobile_control/
├── README.md
├── package.xml, setup.py, setup.cfg
├── config/mobile_control_params.yaml
├── launch/
│   ├── complete_mobile_simulation.launch.py
│   └── mobile_control.launch.py
├── test/test_arbiter.py
├── four_wheel_mobile_control/
│   ├── __init__.py
│   ├── command_arbiter_node.py
│   ├── launch_gate.py
│   ├── system_readiness_node.py
│   └── web_server.py
└── frontend/
    ├── index.html, package.json, package-lock.json
    ├── postcss.config.js, tailwind.config.js, tsconfig.json, vite.config.ts
    └── src/
        ├── App.tsx, main.tsx, index.css
        ├── types/ros.ts
        ├── utils/soundEffects.ts
        ├── services/{manualInputPipeline.ts,rosService.ts}
        └── components/ (16 UI & sensor components)
```

## Dependencies

- **ROS 2 Packages:** `rclpy`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `std_msgs`, `std_srvs`, `nav2_msgs`, `action_msgs`, `controller_manager_msgs`, `lifecycle_msgs`, `tf2_ros`, `rosbridge_server`, `rosapi`, `web_video_server`, `twist_mux`, and the four sibling `four_wheel_*` packages.
- **Frontend Stack:** React `18.3.1`, TypeScript `5.6.3`, Vite `5.4.10`, Tailwind CSS `3.4.14`, `roslib` `1.4.1`, `lucide-react`, `nipplejs`.

## Installation and Build

Build the frontend bundle before `colcon build` (since `setup.py` packages `frontend/dist/` into the ROS 2 share directory):

```bash
cd src/four_wheel_mobile_control/frontend
npm ci
npm run build
cd ../../..
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
colcon build --packages-select four_wheel_mobile_control
source install/setup.bash
```

## Configuration (`config/mobile_control_params.yaml`)

- **`command_arbiter_node`:** `default_mode: "MANUAL"`, `watchdog_timeout: 0.40` s, `heartbeat_timeout: 1.20` s (node default), `default_speed_limit: 1.0`, `max_linear_vel: 1.5` m/s, `max_angular_vel: 2.0` rad/s.
- **`mobile_dashboard_web_server`:** `host: "0.0.0.0"`, `port: 3000`, `rosbridge_port: 9090`, `web_video_port: 8080`.

## Usage and Launch Instructions

Master system launch:

```bash
ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py
```

Attach only the mobile control server stack to an existing simulation:

```bash
ros2 launch four_wheel_mobile_control mobile_control.launch.py
```

Open `http://localhost:3000` (local desktop) or `http://<ROBOT_IP>:3000` (mobile device on the same LAN).

## Topics, Services, Actions, and HTTP Endpoints

- **HTTP (`web_server :3000`):** `GET /` (SPA bundle), `GET /api/health`, `GET /api/config`.
- **Arbiter Subscribed Topics:** `/mobile/cmd_vel` (`Twist`), `/cmd_vel_nav` (`Twist`), `/mobile/heartbeat` (`Empty`), `/mobile/set_mode` (`String`), `/mobile/estop` (`Bool`), `/mobile/speed_limit` (`Float32`).
- **Arbiter Published Topics:** `/cmd_vel` (`Twist`), `/mobile/arbiter_status` (`String` JSON), `/mobile/estop_status` (`Bool`).
- **Arbiter Services Provided / Consumed:** `/mobile/trigger_estop`, `/mobile/reset_estop` (`Trigger`); calls `/exploration/{pause,stop,resume}` and `navigate_to_pose/_action/cancel_goal`.
- **Readiness Topics:** `/system/system_ready` (`Bool`), `/system/readiness_status` (`String` JSON).
- **Dashboard Nav2 Goal Dispatch:** Publishes `/goal_pose` (`geometry_msgs/msg/PoseStamped`); cancels via `/navigate_to_pose/_action/cancel_goal` (`action_msgs/srv/CancelGoal`).

## Examples

Trigger and reset Emergency Stop via ROS 2 service CLI:

```bash
ros2 service call /mobile/trigger_estop std_srvs/srv/Trigger "{}"
ros2 service call /mobile/reset_estop std_srvs/srv/Trigger "{}"
```

## Testing

- **Offline Arbiter & Mock Integration (`TESTED`):** `/usr/bin/python3 -m pytest -v tests/test_mobile_control_suite.py`
- **Frontend Production Build (`TESTED`):** `cd src/four_wheel_mobile_control/frontend && npm run build`
- **Live Browser + Simulation E2E (`TESTED` prior to final doc cleanup):** Verified desktop keyboard/mouse controls, authority lock, WebSocket disconnect zeroing, E-Stop, mobile tabs, and left/right handedness in headless Chrome against live Gazebo.

## Troubleshooting

- If `/mobile/cmd_vel` stops after `0.40 s` during CLI testing, note that `command_arbiter_node` requires continuous streaming (`>= 10 Hz` in the web UI) to keep the monotonic watchdog satisfied.
- If a phone cannot load `:3000` or `:9090`, check LAN UFW firewall rules and Wi-Fi AP isolation (`docs/mobile_network_setup.md`).

## Current Limitations

- Local `rosbridge_websocket` (`:9090`) and HTTP servers have no built-in login or TLS and must stay scoped to trusted private LANs unless fronted by an authenticating reverse proxy.
- External **Dubant** beta server transport and cloud telemetry are not included in this package (`IN DEVELOPMENT` / external).

## Development Status

**Active Development / Beta (`TESTED` local simulation & web interface):** Core arbitration, readiness monitoring, and pixel-art UI are operational locally; external Dubant beta integration remains ongoing.

## Related Packages

- Robot model & Gazebo: [`four_wheel_description`](../four_wheel_description/README.md)
- Wheel kinematics & odometry: [`four_wheel_control`](../four_wheel_control/README.md)
- SLAM & Nav2: [`four_wheel_navigation`](../four_wheel_navigation/README.md)
- Autonomous exploration: [`four_wheel_exploration`](../four_wheel_exploration/README.md)
