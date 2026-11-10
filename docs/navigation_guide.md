# Four-Wheel Steering Autonomous Mobile Robot — Navigation & Exploration Guide

## 1. Mapping: Online Asynchronous SLAM Toolbox

Mapping is handled by `slam_toolbox` in `online_async` mode (`config/mapper_params_online_async.yaml`), providing robust graph-based scan-matching and loop closure under dynamic wheel motion.

### Core Parameters:
- **Solver Plugin:** `solver_plugins::CeresSolver` (Schur Jacobi preconditioner)
- **Base Frame:** `base_footprint`
- **Odom Frame:** `odom`
- **Map Frame:** `map`
- **Scan Topic:** `/scan`
- **Resolution:** `0.05` m (5 cm grid cell size)
- **Max Laser Range:** `12.0` m (truncated to $11.5$ m for boundary clarity)
- **Transform Authority:** Publishes dynamic `map` $\to$ `odom` transform correcting dead-reckoning odometry.

---

## 2. Nav2 Autonomous Navigation Architecture

The Navigation2 stack provides obstacle avoidance, global planning, trajectory generation, and recovery behaviors.

### 2.1 Global Planner (`planner_server`)
- **Plugin:** `nav2_navfn_planner/NavfnPlanner`
- **Algorithm:** Dijkstra / A* wavefront expansion over global costmap
- **Tolerance:** `0.25` m

### 2.2 Local Controller (`controller_server`)
- **Plugin:** `dwb_core::DWBLocalPlanner`
- **Critics:**
  - `RotateToGoal`: Aligns vehicle heading with path segments.
  - `Oscillation`: Prevents back-and-forth thrashing near tight obstacles.
  - `BaseObstacle`: Footprint collision prevention.
  - `GoalAlign`: Heading alignment at destination.
  - `PathAlign`: Strict path following fidelity.
  - `PathDist` & `GoalDist`: Progress toward goal.
- **Velocity Trajectory Sampling:**
  - $v_x \in [-0.20, +0.60]$ m/s
  - $v_y \in [-0.30, +0.30]$ m/s (takes advantage of 4WS crab and swerve capability)
  - $\omega_z \in [-1.50, +1.50]$ rad/s

### 2.3 Costmap Configuration
- **Global Costmap:** Static SLAM map layer, Raycast obstacle layer from `/scan`, Inflation layer ($r_{inf} = 0.55$ m, cost scaling factor $3.0$).
- **Local Costmap:** Rolling window $3.0\text{ m} \times 3.0\text{ m}$ centered on `base_footprint`, resolution $0.05$ m, obstacle and inflation layers.

---

## 3. Frontier-Based Autonomous Exploration (`four_wheel_exploration`)

The exploration agent operates autonomously without human teleoperation, discovering unmapped regions through iterative frontier extraction and Nav2 goal execution.

```
       OccupancyGrid (/map)
               │
               ▼
   ┌───────────────────────┐
   │   Frontier Detector   │
   │  - 8-connected search │
   │  - Component clusters │
   │  - Clearance (EDT)    │
   │  - Goal projection    │
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │   Candidate Ranking   │
   │ Cost = dist + size +  │
   │        clearance      │
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Nav2 Action Dispatch  │
   │   (NavigateToPose)    │
   └───────────┬───────────┘
               │
      Success? ├────────────► Blacklist on failure
               ▼
   Explore Next Frontier
```

### 3.1 Frontier Detection Algorithm
1. Scans `/map` for free cells ($0$) adjacent to unknown cells ($-1$) via 8-connected neighborhood kernels.
2. Clusters adjacent frontier cells using Breadth-First Search (BFS) / connected component labeling.
3. Discards noise clusters smaller than `min_cluster_size` ($5$ cells).

### 3.2 Obstacle Clearance & Safe Goal Projection
1. Computes the Euclidean Distance Transform (EDT) across all obstacles in the costmap.
2. If the cluster centroid has clearance $< 0.32$ m, computes the gradient vector pointing toward free open space and steps outward until safe clearance is verified.

### 3.3 Multi-Criteria Utility Cost Function
Candidate frontiers are ranked using an objective cost function:
$$\text{Cost} = 1.0 \cdot d_{robot} - 0.05 \cdot N_{cluster} - 0.4 \cdot C_{obstacle} + \text{Penalty}_{blacklist}$$

where:
- $d_{robot}$ is Euclidean distance to the robot.
- $N_{cluster}$ is the number of cells in the frontier (prefers large unexplored openings).
- $C_{obstacle}$ is obstacle clearance distance.

### 3.4 Spatial-Temporal Blacklisting
If Nav2 aborts or fails to reach a frontier within `goal_timeout` ($45.0$ s), the spatial coordinate is placed on a blacklist with radius $0.60$ m for $45.0$ seconds, preventing the explorer from getting trapped in unreachable local minima.

