# Four-Wheel Steering Autonomous Mobile Robot — ROS 2 Control Architecture

## 1. Overview

The low-level actuator control pipeline is powered by `ros2_control` combined with the Gazebo Fortress integration plugin `ign_ros2_control`. 

Instead of treating the robot as a differential-drive black box, the robot exposes all 8 physical joints:
- **4 Steering Knuckle Joints** actuated via effort-limited position controllers.
- **4 Traction Wheel Joints** actuated via torque-limited continuous velocity controllers.

```
       [Nav2 /cmd_vel] or [Teleop /cmd_vel]
                     │
                     ▼
       ┌───────────────────────────────┐
       │   four_wheel_kinematics_node   │
       │   - 50Hz Inverse Kinematics   │
       │   - 50Hz Forward Kinematics   │
       │   - Mode switching & limits   │
       └──────────────┬────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
/steering_controller/commands  /drive_controller/commands
 (Float64MultiArray, 4 angles)  (Float64MultiArray, 4 rad/s)
        │                           │
        ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│steering_controller│        │ drive_controller │
│(GroupPositionCtrl│        │(GroupVelocityCtrl│
└─────────┬────────┘        └─────────┬────────┘
          └─────────────┬─────────────┘
                        ▼
             ┌─────────────────────┐
             │  ign_ros2_control   │
             │(Gazebo Hardware IF) │
             └──────────┬──────────┘
                        ▼
             Ignition Physics Model
```

---

## 2. Controller Configuration (`config/ros2_controllers.yaml`)

### 2.1 Controller Manager & Update Rate
```yaml
controller_manager:
  ros__parameters:
    update_rate: 50  # 50 Hz control loop

    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster

    steering_controller:
      type: position_controllers/JointGroupPositionController

    drive_controller:
      type: velocity_controllers/JointGroupVelocityController
```

### 2.2 Joint Allocations
- **`joint_state_broadcaster`**: Publishes all 8 joint positions and velocities to `/joint_states` at 50 Hz.
- **`steering_controller`**:
  ```yaml
  steering_controller:
    ros__parameters:
      joints:
        - fl_steering_joint
        - fr_steering_joint
        - rl_steering_joint
        - rr_steering_joint
  ```
- **`drive_controller`**:
  ```yaml
  drive_controller:
    ros__parameters:
      joints:
        - fl_wheel_joint
        - fr_wheel_joint
        - rl_wheel_joint
        - rr_wheel_joint
  ```

---

## 3. Kinematics Node (`four_wheel_kinematics_node.py`)

The kinematics node bridges standard high-level ROS 2 velocity commands (`/cmd_vel`) and the low-level hardware controllers:

1. **Subscribes to `/cmd_vel`** (`geometry_msgs/msg/Twist`).
2. **Selects Active Steering Mode:**
   - Parameter `steering_mode`: `front_steer`, `four_wheel_steer` (default), `crab`, `swerve`, `in_place`.
   - Automatic fallback: In `four_wheel_steer` mode, pure yaw commands ($|v_x| < 0.01, |\omega_z| > 0.05$) automatically engage tangential in-place rotation for maximum maneuverability.
3. **Applies Kinematic Constraints:**
   - Knuckle angles clipped to $[-\pi/2, \pi/2]$.
   - Wheel rotational speeds clipped to $\pm 18.75$ rad/s ($v \le 1.5$ m/s).
4. **Dispatches Actuator Commands:**
   - `/steering_controller/commands` (`std_msgs/msg/Float64MultiArray`)
   - `/drive_controller/commands` (`std_msgs/msg/Float64MultiArray`)
5. **Computes Closed-Form Odometry:**
   - Subscribes to `/joint_states`.
   - Extracts feedback knuckle positions and wheel velocities.
   - Evaluates decoupled least-squares forward kinematics.
   - Publishes `/odom` (`nav_msgs/msg/Odometry`).
   - Broadcasts dynamic transform `odom` $\to$ `base_footprint` to TF2.

---

## 4. Interactive Teleoperation (`teleop_keyboard.py`)

To manually test all five steering modes in simulation, an interactive curses-based keyboard teleoperation node is provided:

```bash
ros2 run four_wheel_control teleop_keyboard
```

### Controls:
- `w` / `x`: Increase / decrease linear velocity $v_x$
- `a` / `d`: Increase / decrease angular velocity $\omega_z$
- `q` / `e`: Increase / decrease lateral velocity $v_y$ (crab mode)
- `s` / `Space`: Emergency stop (zeros all velocities and centers steering)
- `1`: Switch to Mode A (Front Ackermann Steering)
- `2`: Switch to Mode B (4WS Counter-Phase Steering)
- `3`: Switch to Mode C (Crab Steering)
- `4`: Switch to Mode D (Generalized Swerve Drive)
- `5`: Switch to Mode E (Rotation-In-Place)
