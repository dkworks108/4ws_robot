# Mobile Network Setup & Phone Access Guide
## Project 04 — Four-Wheel Steering Autonomous Mobile Robot

### 1. Network Requirements
1. The host computer running ROS 2 / Gazebo and your smartphone/tablet must be connected to the **same local Wi-Fi / LAN subnet**.
2. Router **AP / Client Isolation** must be disabled so peer-to-peer LAN connections are allowed.
3. All mobile services bind to `0.0.0.0` (all local interfaces) while the host dynamically discovers the active LAN IPv4 address at startup (no hardcoded IP addresses).

---

### 2. Dynamic LAN IP Discovery & Connection URLs

When `ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py` completes startup, `system_readiness_node` prints only the services that are actually listening and verified:

```text
PROJECT 04 — NETWORK SERVICES

Desktop:
http://localhost:3000

Mobile:
http://<CURRENT_LAN_IP>:3000

ROS Bridge:
ws://<CURRENT_LAN_IP>:9090

Camera:
http://<CURRENT_LAN_IP>:8080
```

You can also inspect your current LAN IPv4 address manually at any time:
```bash
ip -4 -o addr show
```

---

### 3. Port Assignments & LAN-Scoped Firewall Security

| Service | Default Port | Protocol | Purpose |
|---|---:|---|---|
| Web dashboard (`web_server`) | `3000` | HTTP | Serves the React/Vite SPA, `/api/config`, and `/api/health` |
| rosbridge WebSocket (`rosbridge_websocket`) | `9090` | WebSocket (TCP) | Bidirectional `roslibjs` telemetry, commands, services, actions |
| Video server (`web_video_server`) | `8080` | HTTP (MJPEG) | Live `/camera/image_raw` stream |

#### Security Warning — Do Not Expose `rosbridge` to the Public Internet
`rosbridge_websocket` allows unauthenticated publishing/subscribing and service/action calls on the ROS 2 graph. **Never** port-forward ports `3000`, `8080`, or `9090` on your internet router, and scope `ufw` rules strictly to private RFC1918 LAN subnets:

```bash
# Allow access ONLY from private LAN subnets (example: 192.168.0.0/16)
sudo ufw allow from 192.168.0.0/16 to any port 3000 proto tcp comment 'Project04 Web Dashboard (LAN only)'
sudo ufw allow from 192.168.0.0/16 to any port 8080 proto tcp comment 'Project04 Video Server (LAN only)'
sudo ufw allow from 192.168.0.0/16 to any port 9090 proto tcp comment 'Project04 Rosbridge WS (LAN only)'
sudo ufw reload
```
*(Replace `192.168.0.0/16` with `10.0.0.0/8` or `172.16.0.0/12` if your local router uses those subnets.)*

Verify listening ports locally:
```bash
ss -tlnp | grep -E '3000|8080|9090'
```

---

### 4. Manual Phone Test Procedure

1. Launch the integrated simulation on the host PC:
   ```bash
   ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py
   ```
2. Wait for `PROJECT 04 SYSTEM READY` and note the printed **Mobile** URL (`http://<CURRENT_LAN_IP>:3000`).
3. On your smartphone (connected to the same Wi-Fi network), open Chrome or Safari and navigate to `http://<CURRENT_LAN_IP>:3000`.
4. **Verify Connection & Telemetry:**
   - Top header badge transitions to **CONNECTED** (`ws://<CURRENT_LAN_IP>:9090`).
   - Operating mode displays **MANUAL**, Steering mode displays **four_wheel_steer**.
   - Live LiDAR scan, occupancy grid map, and MJPEG camera feed render in the **SENSORS** and **MAP** tabs (or side-by-side on tablet/desktop).
5. **Verify Joystick & Dead-Man Switch:**
   - Touch and hold the virtual joystick forward; confirm the robot moves in Gazebo and `/odom` updates.
   - Lift your finger; confirm the robot stops immediately.
   - Touch and hold forward, then close the browser tab or turn off phone Wi-Fi; confirm the 400 ms watchdog stops the robot automatically.
6. **Verify Steering Modes:**
   - Select each of the 5 modes (`Front Ackermann`, `4WS Counter-Phase`, `Crab`, `Generalized Swerve`, `In-Place Spin`) and verify vehicle motion.
7. **Verify Emergency Stop:**
   - Tap the **EMERGENCY STOP** button; confirm immediate stop, locked mode selector, and recovery only after explicit **RESET E-STOP**.
8. **Verify Autonomy:**
   - Switch to **Nav2** and send a goal on the live map, or switch to **Exploration** and tap **Start** -> **Pause** -> **Resume** -> **Stop**.
