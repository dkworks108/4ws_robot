#!/usr/bin/env python3
"""
Autonomous Frontier Exploration Runner and Artifact Generator for 4WS Robot.

Executes autonomous exploration in Gazebo Fortress arena, monitors
frontiers, tracks robot path, saves map via map_saver_cli, and
generates high-resolution visualization screenshots.
"""

import os
import sys

os.environ['PYTHONNOUSERSITE'] = '1'

import time
import math
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
from rclpy.duration import Duration
from rclpy.time import Time
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
            # Rotated wheel patch
            c = math.cos(delta)
            s = math.sin(delta)
            
            # Corner offsets
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

            # Velocity vector arrow
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
        ax.scatter(fx, fy, s=12, c='#ff922b', alpha=0.7, label='Frontier Cells', zorder=4)

    if plan and len(plan[0]) > 0:
        ax.plot(plan[0], plan[1], c='#51cf66', linewidth=2.5, linestyle='--', label='Nav2 Global Path', zorder=5)

    if trajectory and len(trajectory[0]) > 0:
        ax.plot(trajectory[0], trajectory[1], c='#339af0', linewidth=2.0, label='Robot Trajectory', zorder=6)
        # Robot current position
        ax.scatter([trajectory[0][-1]], [trajectory[1][-1]], s=120, c='#ff6b6b', marker='o', edgecolors='#fff', linewidth=2, label='Current Pose', zorder=7)

    if goal:
        ax.scatter([goal[0]], [goal[1]], s=140, c='#ffd43b', marker='*', edgecolors='#000', linewidth=1.5, label='Active Goal', zorder=8)

    # Origin marker
    ax.scatter([0], [0], s=80, c='#845ef7', marker='+', linewidth=2, label='World Origin (0,0)', zorder=9)

    ax.set_title(title, color='#f8f9fa', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("X [meters]", color='#ced4da', fontsize=11)
    ax.set_ylabel("Y [meters]", color='#ced4da', fontsize=11)
    ax.tick_params(colors='#ced4da', labelsize=10)
    ax.grid(True, linestyle=':', alpha=0.3, color='#868e96')

    legend = ax.legend(loc='upper right', facecolor='#212529', edgecolor='#495057', labelcolor='#f8f9fa')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f" -> Generated: {output_path}")


def run_exploration_and_capture():
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"
    maps_dir = os.path.join(ws_root, "maps")
    shots_dir = os.path.join(ws_root, "screenshots")
    os.makedirs(maps_dir, exist_ok=True)
    os.makedirs(shots_dir, exist_ok=True)

    print("=" * 70)
    print("STARTING AUTONOMOUS EXPLORATION RUN & ARTIFACT GENERATOR")
    print("=" * 70)

    # 1. Generate Steering Modes Diagram
    steering_modes_path = os.path.join(shots_dir, "steering_modes.png")
    generate_steering_modes_diagram(steering_modes_path)

    # 2. Cleanup old processes
    subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher",
                    "four_wheel_kinematics_node", "async_slam_toolbox_node", "controller_server",
                    "planner_server", "behavior_server", "bt_navigator", "lifecycle_manager", "explorer_node"],
                   stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    # 3. Launch complete simulation with exploration
    launch_cmd = [
        "ros2", "launch", "four_wheel_description", "complete_simulation.launch.py",
        "headless:=true", "rviz:=false", "slam:=true", "navigation:=true", "exploration:=true"
    ]
    proc = subprocess.Popen(launch_cmd, preexec_fn=os.setsid)

    rclpy.init()
    monitor = ExplorationMonitor()

    try:
        print("[STAGE 1/4] Waiting for simulation, SLAM, Nav2, and Explorer to initialize...")
        t_start = time.time()
        while time.time() - t_start < 45.0:
            monitor.spin_duration(0.5)
            if monitor.latest_map is not None and monitor.latest_odom is not None:
                # Check if map has started publishing
                known = sum(1 for c in monitor.latest_map.data if c >= 0)
                if known > 5000:
                    print(f" -> Map active: {known} known cells.")
                    break

        print("[STAGE 2/4] Robot actively exploring environment...")
        explore_start = time.time()
        explore_duration = 45.0  # Run active exploration for 45s

        last_known = 0
        while time.time() - explore_start < explore_duration:
            monitor.spin_duration(0.5)
            if monitor.latest_map:
                known = sum(1 for c in monitor.latest_map.data if c >= 0)
                if abs(known - last_known) > 1000:
                    elapsed = time.time() - explore_start
                    dist = 0.0
                    for i in range(1, len(monitor.trajectory_x)):
                        dist += math.hypot(monitor.trajectory_x[i] - monitor.trajectory_x[i-1],
                                           monitor.trajectory_y[i] - monitor.trajectory_y[i-1])
                    print(f" -> Exploration t={elapsed:.1f}s | Map Cells={known} | Traveled={dist:.2f}m | Status='{monitor.latest_status}'")
                    last_known = known

        print(f"[STAGE 3/4] Saving SLAM map via nav2_map_server map_saver_cli...")
        map_base_path = os.path.join(maps_dir, "four_wheel_arena_map")
        save_cmd = [
            "ros2", "run", "nav2_map_server", "map_saver_cli",
            "-f", map_base_path,
            "--ros-args", "-p", "save_map_timeout:=10000"
        ]
        save_res = subprocess.run(save_cmd, capture_output=True, text=True)
        print(f"Map saver output: {save_res.stdout.strip()}")

        # Convert PGM to PNG if exists
        pgm_path = map_base_path + ".pgm"
        png_path = map_base_path + ".png"
        if os.path.exists(pgm_path):
            with Image.open(pgm_path) as im:
                im.save(png_path)
            print(f" -> Map saved to: {pgm_path} and {png_path}")

        print("[STAGE 4/4] Rendering publication-grade screenshots...")
        if monitor.latest_map:
            # 1. Clean SLAM Map
            slam_map_path = os.path.join(shots_dir, "slam_map.png")
            render_occupancy_grid(monitor.latest_map, slam_map_path,
                                  title="Project 04 — SLAM Toolbox 2D Arena Occupancy Grid",
                                  trajectory=(monitor.trajectory_x, monitor.trajectory_y))

            # 2. Nav2 Path
            nav2_path_path = os.path.join(shots_dir, "nav2_path.png")
            render_occupancy_grid(monitor.latest_map, nav2_path_path,
                                  title="Project 04 — Nav2 Autonomous Navigation & Global Path Planning",
                                  trajectory=(monitor.trajectory_x, monitor.trajectory_y),
                                  plan=(monitor.latest_plan_x, monitor.latest_plan_y))

            # 3. Frontier Exploration
            frontiers = []
            for m in monitor.frontier_markers:
                for pt in m.points:
                    frontiers.append((pt.x, pt.y))

            expl_path = os.path.join(shots_dir, "autonomous_exploration.png")
            goal = (monitor.latest_plan_x[-1], monitor.latest_plan_y[-1]) if monitor.latest_plan_x else None
            render_occupancy_grid(monitor.latest_map, expl_path,
                                  title="Project 04 — Frontier-Based Autonomous Exploration",
                                  trajectory=(monitor.trajectory_x, monitor.trajectory_y),
                                  plan=(monitor.latest_plan_x, monitor.latest_plan_y),
                                  frontiers=frontiers,
                                  goal=goal)

    finally:
        monitor.destroy_node()
        rclpy.shutdown()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        subprocess.run(["killall", "-9", "ign", "ruby", "gz", "parameter_bridge", "robot_state_publisher",
                        "four_wheel_kinematics_node", "async_slam_toolbox_node", "controller_server",
                        "planner_server", "behavior_server", "bt_navigator", "lifecycle_manager", "explorer_node"],
                       stderr=subprocess.DEVNULL)
        time.sleep(1.0)

    print("=" * 70)
    print("AUTONOMOUS EXPLORATION AND ARTIFACT GENERATION COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    run_exploration_and_capture()
