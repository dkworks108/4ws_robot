# Mobile Dashboard User & Operator Guide
## Four-Wheel Steering Mobile Robot (Project 04)

### 1. Connecting to the Robot

1. Connect your smartphone, tablet, or PC to the **same Wi-Fi network** as the robot workstation.
2. Open any modern browser (Chrome, Safari, Firefox, Edge) and navigate to:
   ```
   http://<ROBOT_IP>:3000
   ```
   *(Example: `http://192.168.31.85:3000` or `http://192.168.31.242:3000`)*
3. The dashboard auto-detects the host IP and connects to the WebSocket bridge (`ws://<ROBOT_IP>:9090`).
4. The top status pill will turn **ONLINE (green)** once connected. If your IP address changes, tap the **Settings icon (⚙️)** in the top right header to specify custom endpoints.

---

### 2. Dashboard Interface Tour

#### A. Emergency Stop Interlock (Pinned at Top)
- **Normal State:** Armed & ready with green indicators.
- **Activating E-Stop:** Tap the prominent red **EMERGENCY STOP** button. All motors immediately receive zero velocity, active Nav2 paths are cancelled, and the exploration state machine is paused.
- **Resetting E-Stop:** Tap **RESET E-STOP** to re-arm the robot into safe `MANUAL` mode.

#### B. Operating Authority Modes
- **MANUAL Mode:** Grants motion authority to the mobile virtual joystick.
- **AUTONOMOUS NAV Mode:** Grants motion authority to Nav2. Click or tap any free space cell on the SLAM map and tap **NAVIGATE** to dispatch a goal.
- **AUTONOMOUS EXPLORE Mode:** Grants motion authority to the Frontier Explorer node. Use the **START**, **PAUSE**, **RESUME**, and **STOP** buttons to map out the arena.

#### C. Steering Mode Selector
Tap any of the 5 modes:
1. **Mode A (Ackermann):** Front wheels steer; rear wheels remain locked parallel.
2. **Mode B (4WS Counter):** Front and rear steer in opposite directions for minimum turning radius.
3. **Mode C (Crab Steer):** All 4 wheels steer parallel for direct diagonal and lateral translation.
4. **Mode D (Swerve):** Universal omnidirectional holonomic planar velocity $(v_x, v_y, \omega_z)$.
5. **Mode E (In-Place Spin):** Wheels pivot tangentially to the chassis center for zero-radius yaw spin.

#### D. Virtual Joystick (Pilot View)
- **Omnidirectional Driving:** Drag the center knob forward/backward/left/right/diagonal.
- **Dead-Man Switch:** Releasing your finger from the joystick immediately halts the robot ($v = 0$).
- **In-Place Rotation:** Hold **CCW** or **CW** to rotate in place.
- **Speed Limit:** Select **25%**, **50%**, **75%**, or **100%** to scale maximum drive speeds.

#### E. Sensors & Camera Stream
- **Live RGB Camera:** Real-time 30 FPS MJPEG feed. Tap **PAUSED** to conserve phone battery or data bandwidth.
- **2D LiDAR Radar:** Visualizes 720 laser scan points up to 12 meters with color-coded safety zones:
  - **Red:** Critical proximity ($< 1.0\text{ m}$)
  - **Amber:** Warning proximity ($< 3.0\text{ m}$)
  - **Cyan:** Clear space ($> 3.0\text{ m}$)

#### F. SLAM Map & Navigation (Mission View)
- **Touch Navigation:** Drag to pan around the map, use **+ / -** buttons to zoom in and out.
- **Point-and-Click Navigation:** Tap anywhere in the free space (white cells) to place a yellow navigation target pin. Tap **NAVIGATE** to dispatch the path through Nav2.
- **Exploration Telemetry:** Displays explored coverage percentage, mapped area in $m^2$, and completed frontier goals in real-time.

