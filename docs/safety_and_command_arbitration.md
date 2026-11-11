# Safety Architecture & Command Arbitration
## Four-Wheel Steering Autonomous Mobile Robot (Project 04)

### 1. The Multi-Authority Hazard Problem

In autonomous robotics systems with manual teleoperation, Nav2 waypoint following, and autonomous frontier exploration, multiple software nodes attempt to command wheel velocities simultaneously. Without centralized command arbitration:
- Manual operator commands would clash with Nav2 obstacle avoidance paths.
- Nav2 commands would clash with frontier exploration exploration sweeps.
- Browser disconnects or packet drops could leave the robot running away with stale nonzero velocity.

---

### 2. Command Arbiter Architecture (`command_arbiter_node.py`)

The **Command Arbiter** acts as the single point of entry to the low-level kinematics controller:

```
[Mobile Virtual Joystick] ────> /mobile/cmd_vel ───┐
                                                    │
[Nav2 Controller Server]  ────> /cmd_vel_nav    ───┼──> [COMMAND ARBITER] ──> /cmd_vel ──> [4WS KINEMATICS]
                                                    │     │  (Watchdog)
[Emergency Stop Button]   ────> /mobile/estop   ───┘     │  (Speed Scale)
                                                          │  (Mode Locks)
                                                          ▼
                                                  /mobile/arbiter_status
```

#### Core Safety Principles:

1. **Single Movement Authority:**
   At any instant, only one entity owns velocity output. If the robot is in `MANUAL` mode, commands on `/cmd_vel_nav` are discarded. If in `AUTONOMOUS_NAV` or `AUTONOMOUS_EXPLORE`, manual joystick commands are ignored until the mode is explicitly changed.

2. **Dead-Man Switch & Watchdog Timeout:**
   In `MANUAL` mode, the operator must actively hold the virtual joystick. The arbiter continuously checks the timestamp of the last received command:
   $$t_{\text{now}} - t_{\text{last\_cmd}} > 0.40\text{ s} \implies \mathbf{v} = \mathbf{0}$$
   If the operator releases the joystick, closes the browser tab, or walks out of Wi-Fi range, the robot automatically comes to an immediate, safe halt within 400 milliseconds.

3. **Latching Emergency Stop Override:**
   Triggering the Emergency Stop (via UI, ROS topic `/mobile/estop`, or service `/mobile/trigger_estop`) latches the system into `ESTOP` state:
   - Output velocity is permanently clamped to zero ($v_x = 0, v_y = 0, \omega_z = 0$).
   - Active Nav2 goals are immediately cancelled.
   - The exploration state machine is paused.
   - All subsequent velocity inputs are rejected until an explicit `/mobile/reset_estop` request is dispatched.

4. **Safe Mode Transitions:**
   Whenever the operating mode changes (e.g. from `AUTONOMOUS_NAV` to `MANUAL`), the arbiter injects a 150 ms zero-velocity lockout buffer to guarantee that dynamic momentum is arrested before the new controller takes ownership.

5. **Speed Limit Clamping:**
   Manual joystick velocity vectors are scaled by the selected speed limit ($25\%, 50\%, 75\%, 100\%$) and clamped against the hard safety ceiling ($v_{\text{max}} = 1.5\text{ m/s}$, $\omega_{\text{max}} = 2.0\text{ rad/s}$).

---

### 3. Physical Hardware Safety Notice

> [!WARNING]
> **Safety Notice for Physical Robot Hardware Deployment:**
> Software-based emergency stop buttons running in web browsers or over Wi-Fi are **NOT safety-rated** under ISO 13849 / ISO 13850 standards. For future deployment on physical robot hardware, a dedicated hardwired electromechanical E-Stop button with a dual-channel safety relay and motor power cut-off circuit must be installed on the vehicle chassis.

