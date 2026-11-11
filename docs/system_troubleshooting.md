# Project 04 — System Troubleshooting Guide

## 1. Environment & Python Issues
- **Symptom:** `ImportError` or NumPy ABI mismatch / `No module named pytest`
- **Fix:** Ensure `export PYTHONNOUSERSITE=1` is set and run tests with `/usr/bin/python3 -m pytest` (avoid custom Conda/venv Python binaries on `$PATH` when running ROS 2 Humble nodes).
  ```bash
  export PYTHONNOUSERSITE=1
  source /opt/ros/humble/setup.bash
  # Optional overlay workspace: source <ROS_EXTRA_OVERLAY>/setup.bash
  source <WORKSPACE_ROOT>/04_four_wheel_steering/install/setup.bash
  ```

## 2. Gazebo Fails to Start or World Rejected
- **Symptom:** `[WORLD ERROR] World SDF file does not exist` or `libgazebo_ros_*` error
- **Fix:** Confirm the world path is valid Ignition Gazebo Fortress SDF (`<sdf>` + `<world>` tags, no Gazebo Classic plugins). Built-in worlds are in `worlds/outdoor_proving_ground.sdf` and `worlds/four_wheel_arena.sdf`.

## 3. Controllers Fail to Activate (`GATE:SIM` Timeout)
- **Symptom:** `ros2_control(9 controllers)` reported missing by `launch_gate` or `system_readiness_node`
- **Diagnosis:** Check `ros2 control list_controllers`. Expect all 9 active:
  `joint_state_broadcaster`, `fl/fr/rl/rr_steering_controller`, `fl/fr/rl/rr_wheel_controller`.
- **Fix:** Check if a previous `ign gazebo` process was still lingering (`pgrep -af "ign gazebo"`). Wait for clean shutdown or run `kill -INT` on leftover Project 04 processes before relaunching.

## 4. Robot Does Not Move When Commanding `/mobile/cmd_vel`
- **Check E-Stop & Mode:** Inspect `/mobile/arbiter_status` (`ros2 topic echo /mobile/arbiter_status --once`).
  - If `estop_active: true`, reset via dashboard **RESET E-STOP** or `ros2 service call /mobile/reset_estop std_srvs/srv/Trigger`.
  - If `operating_mode != "MANUAL"`, switch back to `MANUAL` before using joystick.
  - Because the monotonic watchdog trips after **400 ms**, manual commands must be streamed continuously (e.g., 10 Hz); single one-shot messages stop after 0.4 s.

## 5. Nav2 Does Not Move Robot or Ignores Goals
- **Check Arbiter Authority:** Nav2 publishes to `/cmd_vel_nav`. Ensure `command_arbiter_node` is in `AUTONOMOUS_NAV` or `AUTONOMOUS_EXPLORE` mode (`ros2 topic pub --once /mobile/set_mode std_msgs/msg/String "{data: 'AUTONOMOUS_NAV'}"`).
- **Check Lifecycle State:** Verify `ros2 lifecycle get /bt_navigator` returns `active [3]`.

## 6. Mobile Phone Cannot Reach Dashboard (`:3000`) or WebSocket (`:9090`)
- Confirm both devices are on the same Wi-Fi network (AP isolation off).
- Confirm ports are listening: `ss -tlnp | grep -E '3000|8080|9090'`.
- Check `ufw` firewall rules (see `docs/mobile_network_setup.md`).
- In the dashboard Settings modal (⚙️), verify the WebSocket host matches the current LAN IPv4 printed by `system_readiness_node`.

## 7. Camera Stream Shows Blank / Unavailable
- Verify `use_camera:=true` was passed (default).
- Verify `/camera/image_raw` is publishing (`ros2 topic hz /camera/image_raw`).
- Verify `web_video_server` is listening on port `8080`.

## 8. Monitoring Live Health State
Inspect real-time readiness & runtime health:
```bash
ros2 topic echo /system/readiness_status --once
```
Overall states: `STARTING`, `READY`, `DEGRADED`, `FAILED`, `STOPPING`.

