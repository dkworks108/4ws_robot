# Desktop & Mobile Ground Control Guide
## 4ws_robot — Four-Wheel Steering Mobile Robot (v1.0)

### 1. Connecting to the Robot

1. Launch the integrated system:
   ```bash
   ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py
   ```
2. Open any modern desktop or mobile browser and navigate to:
   ```text
   http://<ROBOT_IP>:3000
   ```
3. The dashboard connects automatically to `ws://<ROBOT_IP>:9090` (`rosbridge_websocket`) and `http://<ROBOT_IP>:8080` (`web_video_server`).
4. The header shows **CONNECTED** (green) alongside Gazebo simulation state, latency, theme toggle, 8-bit SFX mute toggle, settings modal, and keyboard status pill. Tap/click the **Settings** button in the header to configure rosbridge/video ports, keyboard enable & sensitivity, mobile handedness, or SFX mute.

---

### 2. Interface Layouts

#### Desktop Ground-Control Station (`>= 1024px`)
- **Left Sidebar Rail:** Quick focus/navigation across **Control**, **Map & Nav**, **Sensors**, **Telemetry**, **Logs**, and **Settings**.
- **Top Control Row:** Control Authority (`MANUAL`, `NAV2`, `EXPLORE`), 5 Steering Modes (`A. Ackermann` through `E. In-Place Spin` with live pixel wheel icons), Speed Limit (`25%`–`100%`), Manual Control Joystick (`Vx / Vy / ωZ`) + Physical Keyboard widget, Top-Down Robot View (live joint steering angles & velocity vector), and live RGB Camera, 360° LiDAR, and IMU panels.
- **Mission & Telemetry Row:** Interactive SLAM Occupancy Grid (`/map` + `/plan` + `/goal_pose` dispatch & `/navigate_to_pose/_action/cancel_goal` abort), Navigation & Exploration controls (`START` / `PAUSE` / `RESUME` / `STOP`), Odometry Telemetry, System Health checklist, Watchdog monitor, and bottom system event ticker.

#### Mobile One-Handed Interface (`< 1024px`)
- **Sticky Bottom Tabs:** **PILOT**, **MAP**, **SENSORS**, and **TELEMETRY**.
- **Sticky Safety Interlock:** The **System Safety Interlock** banner and **EMERGENCY STOP / RESET E-STOP** remain visible at the top across every mobile tab.
- **Left-Handed / Right-Handed Toggle:** Configurable in the **Settings** modal. Right-handed places the joystick and `CCW`/`CW` rotation buttons under the right thumb with Top-Down Robot View on the left; left-handed mirrors them onto the left side.

---

### 3. Manual Input & Safety Rules

Both Desktop Joystick, Desktop Physical Keyboard, and Mobile Touch Joystick route through a single unified manual pipeline (`/mobile/cmd_vel` at 10 Hz hold, immediate stop on release):

- **Keyboard Mapping:**
  - `W` / `S`: Forward / Reverse (`±linear.x`)
  - `A` / `D`: Left / Right lateral strafe (`±linear.y`)
  - `Q` / `E`: Counter-Clockwise / Clockwise yaw rotation (`±angular.z`)
  - Simultaneous keys combine cleanly (diagonal movement uses normalized planar vector magnitude).
  - `SPACE`: Immediate zero-velocity stop.
- **Keyboard Safety Interlocks:** Keyboard motion is suppressed and all held keys are cleared to zero immediately on E-Stop, authority change away from `MANUAL`, WebSocket disconnect, window `blur`, tab `visibilitychange`, typing inside editable form fields (`input`/`textarea`/`select`), or disabling the keyboard `ON/OFF` toggle.

---

### 4. Visual Theme & 8-Bit Audio

- Retro 8-bit / 16-bit pixel-art palette (`#0F0F23` deep navy background with high-contrast `#FF0000`, `#00FF00`, `#0000FF`, `#FFFF00`, `#FFFFFF`, `#000000` indicators), `Press Start 2P` + `JetBrains Mono` typography, accessible focus rings, and `prefers-reduced-motion` support.
- Web Audio API 8-bit chiptune feedback plays on button presses, mode/authority changes, E-Stop latch/reset, goal dispatch, and WebSocket connect/disconnect, with a header & settings mute toggle (`4ws_sfx_muted`).


