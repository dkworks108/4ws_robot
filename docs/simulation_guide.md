# Four-Wheel Steering Autonomous Mobile Robot — Simulation Guide

## 1. Simulation Environment & Engine

- **Simulator:** Gazebo Fortress (Ignition Gazebo Sim 6.18.0)
- **Physics Engine:** DART
- **Simulation Step Size:** `0.001` s ($1000$ Hz physics solver rate)
- **Real-Time Factor:** Target `1.0` (Empirical `0.95 - 1.00`)
- **Render Engine:** OGRE2 (GPU-accelerated ray tracing and shader rendering)

---

## 2. Gazebo World Design (`worlds/four_wheel_arena.sdf`)

The robot operates within a dedicated $10\text{ m} \times 10\text{ m}$ indoor arena bounded by static perimeter walls and structured with interior obstacle geometries designed to stress test mapping, obstacle clearance, and turning agility.

### Arena Geometry & Elements:
1. **Perimeter Enclosure:** North, South, East, and West boundary walls ($10.2\text{ m} \times 0.2\text{ m} \times 1.0\text{ m}$).
2. **Northeast Cylindrical Pillar:** Center at $(+2.5, +2.2)$, radius $0.4\text{ m}$, height $1.0\text{ m}$.
3. **Northwest Square Crate:** Center at $(-2.2, +2.2)$, size $0.8\text{ m} \times 0.8\text{ m} \times 0.8\text{ m}$.
4. **Southeast Cylindrical Pillar:** Center at $(+2.5, -2.2)$, radius $0.4\text{ m}$, height $1.0\text{ m}$.
5. **Southwest Wall Partition:** Center at $(-2.2, -2.2)$, size $0.2\text{ m} \times 1.8\text{ m} \times 1.0\text{ m}$.
6. **Central Barrier:** Center at $(0.0, 0.0)$, size $1.5\text{ m} \times 0.2\text{ m} \times 0.8\text{ m}$.

### Essential Gazebo Plugins in SDF:
```xml
<plugin filename="ignition-gazebo-physics-system" name="ignition::gazebo::systems::Physics"/>
<plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
<plugin filename="ignition-gazebo-scene-broadcaster-system" name="ignition::gazebo::systems::SceneBroadcaster"/>
<plugin filename="ignition-gazebo-contact-system" name="ignition::gazebo::systems::Contact"/>
<plugin filename="ignition-gazebo-sensors-system" name="ignition::gazebo::systems::Sensors">
  <render_engine>ogre2</render_engine>
</plugin>
<plugin filename="ignition-gazebo-imu-system" name="ignition::gazebo::systems::Imu"/>
```

---

## 3. ROS-Gazebo Bridge Configuration

The `ros_gz_bridge` (`parameter_bridge`) maps sensor streams between Ignition transport and ROS 2 topics:

| Gazebo Transport Topic | Direction | ROS 2 Topic | ROS 2 Message Type |
| :--- | :---: | :--- | :--- |
| `/clock` | `GZ -> ROS` | `/clock` | `rosgraph_msgs/msg/Clock` |
| `/scan` | `GZ -> ROS` | `/scan` | `sensor_msgs/msg/LaserScan` |
| `/imu/data` | `GZ -> ROS` | `/imu/data` | `sensor_msgs/msg/Imu` |
| `/camera/image_raw` | `GZ -> ROS` | `/camera/image_raw` | `sensor_msgs/msg/Image` |

---

## 4. Launching the Simulation

### 4.1 Launch Base Simulation Only (Robot + Gazebo + RViz)
```bash
ros2 launch four_wheel_description gazebo.launch.py
```

### 4.2 Launch Headless Mode (Fast physics, CI/CD testing)
```bash
ros2 launch four_wheel_description gazebo.launch.py headless:=true rviz:=false
```

### 4.3 Launch Complete End-to-End Autonomous System
This unified launch file sequentially initializes the robot physics, controllers, SLAM Toolbox, Nav2 navigation stack, and the autonomous frontier exploration agent:
```bash
ros2 launch four_wheel_description complete_simulation.launch.py
```
Arguments:
- `headless:=true|false` (default `false`)
- `rviz:=true|false` (default `true`)
- `slam:=true|false` (default `true`)
- `navigation:=true|false` (default `true`)
- `exploration:=true|false` (default `true`)
