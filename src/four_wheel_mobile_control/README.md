# `four_wheel_mobile_control`

Master system orchestrator, safety command arbiter, readiness monitor, HTTP static dashboard server, and retro pixel-art React + TypeScript + Vite desktop/mobile ground-control interface for Project 04.

> [!WARNING]
> **BETA NOTICE:** External server-based control via the **Dubant** control/server system is in active **BETA** development and is not bundled in this local runtime package. Current web telemetry and teleoperation in this package use local LAN HTTP, `rosbridge_websocket`, and `web_video_server` (see [`docs/dubant_beta_integration.md`](../../docs/dubant_beta_integration.md)).

---

## 1. Purpose

Serves as the primary user-facing entry point (`complete_mobile_simulation.launch.py`), centralized safety authority (`command_arbiter_node`), system health gatekeeper (`launch_gate` and `system_readiness_node`), and web ground-control server (`web_server` + `frontend/`).

---

## 2. Architecture and Key Components

```mermaid
flowchart TB
    Frontend["React + TypeScript + Vite UI\n(Desktop Workstation & Mobile One-Handed)"]
    WebSrv["web_server (:3000)\nHTTP + /api/health + /api/config"]
    VideoSrv["web_video_server (:8080)\nMJPEG /camera/image_raw"]
    Rosbridge["rosbridge_websocket (:9090)"]

    Frontend <-->|"UI Assets"| WebSrv
    Frontend <--|"MJPEG Video"| VideoSrv
    Frontend <-->|"JSON WebSocket Topics/Services"| Rosbridge

    Rosbridge -->|"/mobile/cmd_vel (10 Hz)"| Arbiter["command_arbiter_node (50 Hz)"]
    Nav2["Nav2 (/cmd_vel_nav)"] --> Arbiter
    Arbiter -->|"/cmd_vel"| Kin["four_wheel_kinematics_node"]
    Ready["system_readiness_node"] -->|"/system/readiness_status"| Rosbridge
```

### ROS 2 Nodes (`four_wheel_mobile_control/`)

| Executable | Role |
| :--- | :--- |
| `command_arbiter_node` | Single-authority multiplexer (`MANUAL`, `AUTONOMOUS_NAV`, `AUTONOMOUS_EXPLORE`, `ESTOP`), `0.40 s` monotonic watchdog, `0.15 s` mode-transition zero-hold lockout, speed scaling (`0.1-1.0`), velocity clamping (`1.5 m/s`, `2.0 rad/s`), and Nav2/Exploration cancellation on E-Stop |
| `web_server` | Serves built Vite bundle on `0.0.0.0:3000`, exposes `/api/health` and `/api/config`, and discovers host LAN IPv4 addresses |
| `system_readiness_node` | Verifies active controllers, Nav2 lifecycle states, TF frames, HTTP `:3000`, WebSocket `:9090`, and Video `:8080`, publishing JSON health (`STARTING`, `READY`, `DEGRADED`, `FAILED`, `STOPPING`) on `/system/readiness_status` |
| `launch_gate` | Pre-checks simulation, SLAM, and Nav2 readiness gates between master launch stages (`--stage sim|slam|nav2`) |

### Frontend (`frontend/src/`)

- **Services:** `manualInputPipeline.ts` (shared Desktop Keyboard `W/A/S/D/Q/E/Space` + Desktop Mouse Joystick + Mobile Touch Joystick publisher at `10 Hz` with focus, visibility, authority, E-Stop, and disconnect zeroing) and `rosService.ts` (Rosbridge topics, `/goal_pose` dispatch, `/navigate_to_pose/_action/cancel_goal` cancel, socket teardown safety).
- **Audio & Design:** Retro 8-bit/16-bit arcade UI (`Press Start 2P` + `JetBrains Mono`) and pure Web Audio API 8-bit sound effects (`utils/soundEffects.ts`) with mute persistence.
- **Responsive Views (`App.tsx`):** Desktop Console (`>= 1024px` with sidebar rail, dual-input manual card, robot view, camera, LiDAR, IMU, SLAM map, Nav2/exploration, telemetry/health/watchdog, status ticker) and Mobile One-Handed UI (`< 1024px` with sticky E-Stop, `PILOT`/`MAP`/`SENSORS`/`TELEMETRY` tabs, and Left/Right-Handed mirroring).

---

## 3. Dependencies and Build

**ROS Dependencies:** `rclpy`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `std_msgs`, `std_srvs`, `nav2_msgs`, `action_msgs`, `controller_manager_msgs`, `lifecycle_msgs`, `tf2_ros`, `rosbridge_server`, `rosapi`, `web_video_server`, `twist_mux`, and the four sibling `four_wheel_*` packages.

**Frontend Build (must be built before `colcon build` so `setup.py` bundles `frontend/dist/`):**

```bash
cd src/four_wheel_mobile_control/frontend
npm ci
npm run build
```

**ROS Package Build:**

```bash
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
colcon build --packages-select four_wheel_mobile_control
source install/setup.bash
```

---

## 4. Execution and Configuration

Launch the full integrated simulation + dashboard stack:

```bash
ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py
```

Attach only the mobile control server stack to an already running simulation:

```bash
ros2 launch four_wheel_mobile_control mobile_control.launch.py
```

Open `http://localhost:3000` (workstation) or `http://<ROBOT_IP>:3000` (mobile device on the same LAN). Defaults in `config/mobile_control_params.yaml`: `port: 3000`, `rosbridge_port: 9090`, `web_video_port: 8080`, `watchdog_timeout: 0.40 s`, `max_linear_vel: 1.5 m/s`, `max_angular_vel: 2.0 rad/s`.

---

## 5. Testing and Known Limitations

- **Offline arbiter & interface tests (`TESTED`):** `/usr/bin/python3 -m pytest -v tests/test_mobile_control_suite.py` and `colcon test --packages-select four_wheel_mobile_control`.
- **Browser + Live ROS 2 E2E (`TESTED`):** Verified across desktop, tablet, and mobile viewports in headless Chrome against live Gazebo Fortress (`W/A/S/D/Q/E/Space`, joystick, blur/disconnect/authority gates, E-Stop latch/reset, left/right handedness, mobile tabs, and zero console errors).
- **Known limitations:** Local `rosbridge` communicates over plaintext `ws://` without user login; Dubant server/cloud control (`docs/dubant_beta_integration.md`) is an external beta component not yet implemented in this codebase.
