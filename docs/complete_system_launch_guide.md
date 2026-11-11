# Project 04 — Complete System Launch Guide

## 1. Environment Setup

Run these commands in your terminal (or place them in `~/.bashrc` if desired):

```bash
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
# Optional overlay workspace if additional ROS 2 packages are installed outside /opt/ros/humble:
# source <ROS_EXTRA_OVERLAY>/setup.bash
cd <WORKSPACE_ROOT>/04_four_wheel_steering
source install/setup.bash
```

---

## 2. Single-Command Full System Launch

Start the entire Project 04 system (Gazebo Fortress, 8-DOF 4WS/4WD robot, `ros2_control`, kinematics & odometry, LiDAR/IMU/RGB camera, SLAM Toolbox, Nav2, Frontier Exploration, Command Arbiter, rosbridge WebSocket, MJPEG Video Server, React Mobile Dashboard, RViz2, and Readiness Monitor) with:

```bash
ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py
```

### Expected Startup Sequence
1. **Stage 1–4 (Simulation & Hardware Abstraction):** Validates the SDF world, launches Gazebo Fortress, spawns the 4WS/4WD robot, activates `joint_state_broadcaster` + 4 steering controllers + 4 wheel drive controllers, starts `four_wheel_kinematics_node`, and bridges `/clock`, `/scan`, `/imu/data`, `/camera/image_raw`, and `/camera/camera_info`.
2. **Gate SIM:** Verifies advancing `/clock`, `/odom`, `/scan`, `/imu/data`, all 9 active controllers, and TF `odom -> base_footprint`.
3. **Stage 5 & 8 (SLAM & Mobile Control Stack):** Starts `slam_toolbox` (online async), `command_arbiter_node`, `rosbridge_websocket` (`:9090`), `rosapi`, `web_video_server` (`:8080`), `web_server` (`:3000`), and `system_readiness_node`.
4. **Gate SLAM:** Verifies `/map` and TF `map -> odom`.
5. **Stage 6 (Nav2):** Starts `controller_server`, `planner_server`, `behavior_server`, `bt_navigator` (remapped to `/cmd_vel_nav`), and `lifecycle_manager_navigation`.
6. **Gate NAV2:** Verifies all 4 Nav2 lifecycle nodes reach `ACTIVE` and `navigate_to_pose` action server is ready.
7. **Stage 7 & 9 (Exploration & RViz2):** Starts `explorer_node` (`autostart=false` by default) and `rviz2` (unless `headless=true` or `use_rviz=false`).
8. **Readiness Banner:** `system_readiness_node` prints `PROJECT 04 SYSTEM READY` along with verified Desktop and Mobile LAN URLs.

---

## 3. Launch Arguments

| Argument | Default | Description |
|---|---|---|
| `world` | `outdoor_proving_ground.sdf` | Path to a Gazebo Fortress SDF world file |
| `headless` | `false` | Run Gazebo without GUI (`-s -r`) |
| `use_rviz` | `true` | Start RViz2 (automatically skipped when `headless:=true`) |
| `use_slam` | `true` | Enable SLAM Toolbox online mapping |
| `use_navigation` | `true` | Enable Nav2 autonomous navigation stack |
| `use_exploration` | `true` | Enable frontier exploration engine |
| `use_mobile_control` | `true` | Enable mobile dashboard, rosbridge, video server, and arbiter |
| `use_camera` | `true` | Enable RGB camera bridge and MJPEG streaming |
| `camera_width` | `640` | Camera horizontal resolution (px) |
| `camera_height` | `480` | Camera vertical resolution (px) |
| `use_sim_time` | `true` | Synchronize nodes to Gazebo `/clock` |
| `exploration_autostart` | `false` | Auto-start frontier exploration immediately on launch |
| `web_port` | `3000` | Mobile web dashboard HTTP port |
| `rosbridge_port` | `9090` | rosbridge WebSocket port |
| `video_port` | `8080` | MJPEG video server HTTP port |

---

## 4. Common Launch Variants

### Low-Resource / Headless Mode (Recommended for Laptop Battery or SSH)
```bash
ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py headless:=true use_rviz:=false
```

### Custom World Selection
```bash
ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py \
  world:="$(pwd)/worlds/four_wheel_arena.sdf"
```

### Lightweight Camera Resolution (320×240)
```bash
ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py camera_width:=320 camera_height:=240
```

---

## 5. Clean Shutdown & Restart

Press **`Ctrl+C`** in the launch terminal. ROS 2 `launch` sends `SIGINT` cleanly to all child processes (`ign gazebo`, `ros2` nodes, `rosbridge_websocket`, `web_video_server`, `web_server`, `rviz2`).

Verify no orphan Project 04 processes remain before restarting:
```bash
pgrep -af "four_wheel_|rosbridge_websocket|web_video_server|ign gazebo"
```
No workspace cleanup is needed between restarts; simply rerun `ros2 launch four_wheel_mobile_control complete_mobile_simulation.launch.py`.

