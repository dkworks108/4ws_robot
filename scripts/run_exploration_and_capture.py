#!/usr/bin/env python3
"""
Autonomous Frontier Exploration Runner and Artifact Generator for 4WS Robot.

Executes autonomous exploration in the Outdoor Proving Ground Gazebo Fortress world,
monitors frontiers, tracks robot trajectory, captures live RViz2 views, saves maps via
map_saver_cli, and generates high-resolution visualization screenshots.
"""

import os
import sys

# Isolate from user-level numpy 2.x mismatch with ROS 2 Humble
os.environ['PYTHONNOUSERSITE'] = '1'
sys.path = [p for p in sys.path if not ('.local' in p and 'site-packages' in p)]

import time
import math
import shutil
import subprocess
import signal
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from visualization_msgs.msg import MarkerArray
from std_msgs.msg import String


class ExplorationMonitor(Node):
    def __init__(self):
        super().__init__('exploration_monitor')

        self.latest_map = None
        self.latest_odom = None
        self.trajectory_x = []
        self.trajectory_y = []
        self.latest_plan_x = []
        self.latest_plan_y = []
        self.frontier_markers = []
        self.latest_status = ""

        self.create_subscription(OccupancyGrid, '/map', self.cb_map, 10)
        self.create_subscription(Odometry, '/odom', self.cb_odom, 10)
        self.create_subscription(Path, '/plan', self.cb_plan, 10)
        self.create_subscription(MarkerArray, '/exploration/frontiers', self.cb_frontiers, 10)
        self.create_subscription(String, '/exploration/status', self.cb_status, 10)

    def cb_map(self, msg: OccupancyGrid):
        self.latest_map = msg

    def cb_odom(self, msg: Odometry):
        self.latest_odom = msg
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        if not self.trajectory_x or math.hypot(px - self.trajectory_x[-1], py - self.trajectory_y[-1]) > 0.05:
            self.trajectory_x.append(px)
            self.trajectory_y.append(py)

    def cb_plan(self, msg: Path):
        self.latest_plan_x = [p.pose.position.x for p in msg.poses]
        self.latest_plan_y = [p.pose.position.y for p in msg.poses]

    def cb_frontiers(self, msg: MarkerArray):
        self.frontier_markers = msg.markers

    def cb_status(self, msg: String):
        self.latest_status = msg.data

    def spin_duration(self, seconds: float):
        start = time.time()
        while time.time() - start < seconds and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)


def generate_steering_modes_diagram(output_path: str):
    """Generate high-fidelity technical diagram of all 5 steering modes."""
    fig, axes = plt.subplots(1, 5, figsize=(22, 5), dpi=150)
    fig.patch.set_facecolor('#1a1a24')

    modes = [
        ("Mode A: Front Ackermann", [math.radians(25), math.radians(18), 0.0, 0.0], "Rear axle ICR\nStandard car steering"),
        ("Mode B: 4WS Counter-Phase", [math.radians(22), math.radians(22), -math.radians(22), -math.radians(22)], "Center-lateral ICR\nTight turning radius"),
        ("Mode C: Crab Steering", [math.radians(35), math.radians(35), math.radians(35), math.radians(35)], "Parallel steering\nDiagonal translation"),
        ("Mode D: Generalized Swerve", [math.radians(30), math.radians(15), -math.radians(10), -math.radians(25)], "Arbitrary ICR (Vx, Vy, Wz)\nFull holonomic agility"),
        ("Mode E: Rotation-In-Place", [-math.radians(45), math.radians(45), math.radians(45), -math.radians(45)], "Center ICR (0,0)\nZero-radius pure spin")
    ]

    L = 0.36
    W = 0.36
    wheel_w = 0.04
    wheel_l = 0.12

    positions = [
        (L / 2, W / 2, "FL"),
        (L / 2, -W / 2, "FR"),
        (-L / 2, W / 2, "RL"),
        (-L / 2, -W / 2, "RR")
    ]

    for ax, (title, deltas, desc) in zip(axes, modes):
        ax.set_facecolor('#232332')
        ax.set_aspect('equal')
        ax.set_xlim(-0.45, 0.45)
        ax.set_ylim(-0.45, 0.45)
        ax.set_title(title, color='#00d4ff', fontsize=12, fontweight='bold', pad=10)

        # Draw chassis body
        chassis = patches.Rectangle((-L/2, -W/2), L, W, linewidth=2, edgecolor='#5c7cfa', facecolor='#2b304f', alpha=0.7)
        ax.add_patch(chassis)

        # Draw coordinate axes at center
        ax.arrow(0, 0, 0.12, 0, head_width=0.03, head_length=0.03, fc='#ff6b6b', ec='#ff6b6b', zorder=5)
        ax.arrow(0, 0, 0, 0.12, head_width=0.03, head_length=0.03, fc='#51cf66', ec='#51cf66', zorder=5)
        ax.text(0.14, 0, 'X', color='#ff6b6b', fontsize=9, fontweight='bold', va='center')
        ax.text(0, 0.14, 'Y', color='#51cf66', fontsize=9, fontweight='bold', ha='center')

        # Draw wheels
        for (wx, wy, name), delta in zip(positions, deltas):
            c = math.cos(delta)
            s = math.sin(delta)
            
            dx = wheel_l / 2
            dy = wheel_w / 2
            pts = np.array([
                [-dx, -dy],
                [dx, -dy],
                [dx, dy],
                [-dx, dy]
            ])
            rot_pts = np.dot(pts, np.array([[c, s], [-s, c]])) + np.array([wx, wy])
            wheel_patch = patches.Polygon(rot_pts, closed=True, facecolor='#ffa94d', edgecolor='#ffd43b', linewidth=1.5, zorder=6)
            ax.add_patch(wheel_patch)

            v_len = 0.09
            ax.arrow(wx, wy, v_len * c, v_len * s, head_width=0.02, head_length=0.02, fc='#38d9a9', ec='#38d9a9', linewidth=1.5, zorder=7)
            ax.text(wx + 0.03 * np.sign(wx), wy + 0.03 * np.sign(wy), name, color='#adb5bd', fontsize=8, ha='center', va='center')

        ax.text(0, -0.38, desc, color='#f1f3f5', fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#11121c', edgecolor='#495057', alpha=0.8))
        ax.tick_params(colors='#868e96', labelsize=8)
        ax.grid(True, linestyle='--', alpha=0.2, color='#adb5bd')

    plt.suptitle("Project 04 — Four-Wheel Steering Kinematics & Locomotion Modes", color='#f8f9fa', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f" -> Generated: {output_path}")


def render_occupancy_grid(grid: OccupancyGrid, output_path: str, title: str,
                          trajectory=None, plan=None, frontiers=None, goal=None):
    """Render high-resolution 2D map with optional overlays."""
    width = grid.info.width
    height = grid.info.height
    res = grid.info.resolution
    origin_x = grid.info.origin.position.x
    origin_y = grid.info.origin.position.y

    data = np.array(grid.data, dtype=np.int8).reshape((height, width))

    # RGB canvas
    # -1 (unknown) -> #495057 (gray)
    # 0 (free) -> #f8f9fa (light)
    # 100 (obstacle) -> #212529 (dark)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[data == -1] = [120, 125, 135]      # Unknown: neutral slate gray
    img[data == 0] = [240, 243, 246]       # Free space: clean off-white
    img[data > 50] = [33, 37, 41]          # Obstacles / walls: charcoal black
    img[(data > 0) & (data <= 50)] = [173, 181, 189]  # Probability transitions

    extent = [origin_x, origin_x + width * res, origin_y, origin_y + height * res]

    fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
    fig.patch.set_facecolor('#1a1a24')
    ax.set_facecolor('#232332')

    ax.imshow(img, origin='lower', extent=extent)

    # Overlays
    if frontiers:
        fx = [p[0] for p in frontiers]
        fy = [p[1] for p in frontiers]
        ax.scatter(fx, fy, s=14, c='#ff922b', alpha=0.7, label='Frontier Exploration Targets', zorder=4)

    if plan and len(plan[0]) > 0:
        ax.plot(plan[0], plan[1], c='#51cf66', linewidth=2.5, linestyle='--', label='Nav2 Global Planned Path', zorder=5)

    if trajectory and len(trajectory[0]) > 0:
        ax.plot(trajectory[0], trajectory[1], c='#339af0', linewidth=2.0, label='Robot Trajectory Traveled', zorder=6)
        # Robot current position
        ax.scatter([trajectory[0][-1]], [trajectory[1][-1]], s=130, c='#ff6b6b', marker='o', edgecolors='#fff', linewidth=2, label='Current Robot Pose', zorder=7)

    if goal:
        ax.scatter([goal[0]], [goal[1]], s=150, c='#ffd43b', marker='*', edgecolors='#000', linewidth=1.5, label='Active Frontier Goal', zorder=8)

    # Origin marker
    ax.scatter([0], [0], s=90, c='#845ef7', marker='+', linewidth=2, label='Spawning Origin (0,0)', zorder=9)

    ax.set_title(title, color='#f8f9fa', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("X Position [meters]", color='#ced4da', fontsize=11)
    ax.set_ylabel("Y Position [meters]", color='#ced4da', fontsize=11)
    ax.tick_params(colors='#ced4da', labelsize=10)
    ax.grid(True, linestyle=':', alpha=0.3, color='#868e96')

    ax.legend(loc='upper right', facecolor='#212529', edgecolor='#495057', labelcolor='#f8f9fa', fontsize=9)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f" -> Generated: {output_path}")


def run_exploration_and_capture():
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"
    world_file = os.path.join(ws_root, "worlds", "outdoor_proving_ground.sdf")
    maps_dir = os.path.join(ws_root, "maps")
    shots_dir = os.path.join(ws_root, "screenshots")
    artifact_dir = "/home/bumble/.gemini/antigravity/brain/eb11fa95-96d2-46db-80ff-1f4e563c69c3"
    
    os.makedirs(maps_dir, exist_ok=True)
    os.makedirs(shots_dir, exist_ok=True)
    os.makedirs(artifact_dir, exist_ok=True)

    print("=" * 75)
    print("STARTING AUTONOMOUS TESTING & SCREENSHOT CAPTURE IN OUTDOOR PROVING GROUND")
    print(f"Target World: {world_file}")
    print("=" * 75)

    # 1. Generate Steering Modes Diagram
    steering_modes_path = os.path.join(shots_dir, "steering_modes.png")
    generate_steering_modes_diagram(steering_modes_path)
    shutil.copy2(steering_modes_path, os.path.join(artifact_dir, "steering_modes.png"))

    # 2. Cleanup old processes
    print("[CLEANUP] Terminating any stale ROS 2 / Gazebo processes...")
    subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher",
                    "four_wheel_kinematics_node", "async_slam_toolbox_node", "controller_server",
                    "planner_server", "behavior_server", "bt_navigator", "lifecycle_manager", "explorer_node", "rviz2"],
                   stderr=subprocess.DEVNULL)
    time.sleep(1.5)

    # 3. Launch complete simulation with exploration targeting outdoor_proving_ground.sdf
    launch_cmd = [
        "ros2", "launch", "four_wheel_description", "complete_simulation.launch.py",
        f"world:={world_file}",
        "headless:=true", "rviz:=false", "slam:=true", "navigation:=true", "exploration:=true"
    ]
    print(f"[LAUNCH] Executing: {' '.join(launch_cmd)}")
    proc = subprocess.Popen(launch_cmd, preexec_fn=os.setsid)

    rclpy.init()
    monitor = ExplorationMonitor()

    try:
        print("\n[STAGE 1/4] Waiting for Gazebo Fortress, SLAM Toolbox, Nav2, and Explorer...")
        t_start = time.time()
        map_ready = False
        while time.time() - t_start < 55.0:
            monitor.spin_duration(0.5)
            if monitor.latest_map is not None and monitor.latest_odom is not None:
                known = sum(1 for c in monitor.latest_map.data if c >= 0)
                if known > 4000:
                    print(f" -> SLAM Map online & active: {known} cells mapped.")
                    map_ready = True
                    break

        if not map_ready:
            print(" -> Proceeding with partial map initialization...")

        print("\n[STAGE 2/4] Robot actively navigating and exploring outdoor proving ground...")
        explore_start = time.time()
        explore_duration = 50.0  # Explore for 50 seconds
        rviz_captured = False

        last_known = 0
        while time.time() - explore_start < explore_duration:
            monitor.spin_duration(0.5)
            elapsed = time.time() - explore_start

            if monitor.latest_map:
                known = sum(1 for c in monitor.latest_map.data if c >= 0)
                if abs(known - last_known) > 800:
                    dist = 0.0
                    for i in range(1, len(monitor.trajectory_x)):
                        dist += math.hypot(monitor.trajectory_x[i] - monitor.trajectory_x[i-1],
                                           monitor.trajectory_y[i] - monitor.trajectory_y[i-1])
                    print(f" -> t={elapsed:4.1f}s | Map Cells={known:6d} | Traveled={dist:5.2f}m | Status='{monitor.latest_status}'")
                    last_known = known

            # Capture live RViz2 screenshot at ~25 seconds of exploration
            if elapsed > 25.0 and not rviz_captured:
                print(" -> Launching isolated RViz2 instance in xvfb to capture live 3D sensor feed...")
                rviz_cfg = os.path.join(ws_root, "src", "four_wheel_description", "rviz", "four_wheel.rviz")
                rviz_shot = os.path.join(shots_dir, "outdoor_proving_ground_rviz.png")
                rviz_cmd = (
                    f"source /opt/ros/humble/setup.bash && "
                    f"source {ws_root}/install/setup.bash && "
                    f"xvfb-run -a -s '-screen 0 1920x1080x24' bash -c '"
                    f"  rviz2 -d {rviz_cfg} & "
                    f"  RV_PID=$!; "
                    f"  sleep 7; "
                    f"  scrot {rviz_shot}; "
                    f"  kill -9 $RV_PID "
                    f"'"
                )
                try:
                    subprocess.run(rviz_cmd, shell=True, executable="/bin/bash", capture_output=True, timeout=20)
                    if os.path.exists(rviz_shot):
                        shutil.copy2(rviz_shot, os.path.join(artifact_dir, "outdoor_proving_ground_rviz.png"))
                        shutil.copy2(rviz_shot, os.path.join(shots_dir, "rviz_model.png"))
                        shutil.copy2(rviz_shot, os.path.join(artifact_dir, "rviz_model.png"))
                        print(f" -> Successfully captured live RViz2 view: {rviz_shot}")
                except Exception as e:
                    print(f" -> RViz capture warning: {e}")
                rviz_captured = True

        print(f"\n[STAGE 3/4] Saving high-resolution SLAM maps via nav2_map_server map_saver_cli...")
        map_base_path = os.path.join(maps_dir, "outdoor_proving_ground_map")
        save_cmd = [
            "ros2", "run", "nav2_map_server", "map_saver_cli",
            "-f", map_base_path,
            "--ros-args", "-p", "save_map_timeout:=10000"
        ]
        save_res = subprocess.run(save_cmd, capture_output=True, text=True)
        print(f"Map saver output: {save_res.stdout.strip()}")

        # Convert PGM to PNG and copy to four_wheel_arena_map as well
        pgm_path = map_base_path + ".pgm"
        png_path = map_base_path + ".png"
        if os.path.exists(pgm_path):
            with Image.open(pgm_path) as im:
                im.save(png_path)
            shutil.copy2(pgm_path, os.path.join(maps_dir, "four_wheel_arena_map.pgm"))
            shutil.copy2(map_base_path + ".yaml", os.path.join(maps_dir, "four_wheel_arena_map.yaml"))
            shutil.copy2(png_path, os.path.join(maps_dir, "four_wheel_arena_map.png"))
            shutil.copy2(png_path, os.path.join(artifact_dir, "outdoor_proving_ground_map.png"))
            print(f" -> Map files successfully saved to: {map_base_path}.*")

        print("\n[STAGE 4/4] Rendering publication-grade screenshots with Matplotlib overlays...")
        if monitor.latest_map:
            # 1. Clean SLAM Map
            slam_shot = os.path.join(shots_dir, "outdoor_proving_ground_slam_map.png")
            render_occupancy_grid(monitor.latest_map, slam_shot,
                                  title="Project 04 — Outdoor Proving Ground SLAM Toolbox Occupancy Grid",
                                  trajectory=(monitor.trajectory_x, monitor.trajectory_y))
            shutil.copy2(slam_shot, os.path.join(shots_dir, "slam_map.png"))
            shutil.copy2(slam_shot, os.path.join(artifact_dir, "outdoor_proving_ground_slam_map.png"))
            shutil.copy2(slam_shot, os.path.join(artifact_dir, "slam_map.png"))

            # 2. Nav2 Autonomous Planned Path
            nav2_shot = os.path.join(shots_dir, "outdoor_proving_ground_nav2_path.png")
            render_occupancy_grid(monitor.latest_map, nav2_shot,
                                  title="Project 04 — Nav2 Autonomous Navigation in Outdoor Proving Ground",
                                  trajectory=(monitor.trajectory_x, monitor.trajectory_y),
                                  plan=(monitor.latest_plan_x, monitor.latest_plan_y))
            shutil.copy2(nav2_shot, os.path.join(shots_dir, "nav2_path.png"))
            shutil.copy2(nav2_shot, os.path.join(artifact_dir, "outdoor_proving_ground_nav2_path.png"))
            shutil.copy2(nav2_shot, os.path.join(artifact_dir, "nav2_path.png"))

            # 3. Frontier Exploration Map
            frontiers = []
            for m in monitor.frontier_markers:
                for pt in m.points:
                    frontiers.append((pt.x, pt.y))

            expl_shot = os.path.join(shots_dir, "outdoor_proving_ground_exploration.png")
            goal = (monitor.latest_plan_x[-1], monitor.latest_plan_y[-1]) if monitor.latest_plan_x else None
            render_occupancy_grid(monitor.latest_map, expl_shot,
                                  title="Project 04 — Autonomous Frontier Exploration & Tactical Maze Mapping",
                                  trajectory=(monitor.trajectory_x, monitor.trajectory_y),
                                  plan=(monitor.latest_plan_x, monitor.latest_plan_y),
                                  frontiers=frontiers,
                                  goal=goal)
            shutil.copy2(expl_shot, os.path.join(shots_dir, "autonomous_exploration.png"))
            shutil.copy2(expl_shot, os.path.join(artifact_dir, "outdoor_proving_ground_exploration.png"))
            shutil.copy2(expl_shot, os.path.join(artifact_dir, "autonomous_exploration.png"))

        # Copy all 3D renders to artifact directory to ensure all visual assets are current
        for r_name in ["robot_isometric_3d.png", "robot_top_3d.png", "robot_front_3d.png",
                       "robot_side_3d.png", "robot_steering_counterphase.png",
                       "robot_steering_crab.png", "robot_steering_inplace.png"]:
            src_f = os.path.join(shots_dir, r_name)
            if os.path.exists(src_f):
                shutil.copy2(src_f, os.path.join(artifact_dir, r_name))

    finally:
        monitor.destroy_node()
        rclpy.shutdown()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher",
                        "four_wheel_kinematics_node", "async_slam_toolbox_node", "controller_server",
                        "planner_server", "behavior_server", "bt_navigator", "lifecycle_manager", "explorer_node", "rviz2"],
                       stderr=subprocess.DEVNULL)
        time.sleep(1.5)

    print("=" * 75)
    print("AUTONOMOUS EXPLORATION AND SCREENSHOT GENERATION COMPLETE")
    print(f"Screenshots saved to: {shots_dir} and {artifact_dir}")
    print("=" * 75)


if __name__ == '__main__':
    run_exploration_and_capture()
