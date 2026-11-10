#!/usr/bin/env python3
"""
High-Resolution 3D Multi-Angle Renderer for 4WS Mobile Robot.
Generates publication-quality 3D views of the robot in various steering configurations.
"""

import os
import sys
import math
import numpy as np
from PIL import Image

# Ensure clean system-site packages
sys.path = [p for p in sys.path if not ('.local' in p and 'site-packages' in p)]
os.environ.setdefault('PYTHONNOUSERSITE', '1')

import pybullet as p


def setup_pybullet():
    cid = p.connect(p.DIRECT)
    p.setGravity(0, 0, -9.81)
    return cid


def render_view(rid, target_pos, distance, yaw, pitch, width=800, height=600):
    view_matrix = p.computeViewMatrixFromYawPitchRoll(
        cameraTargetPosition=target_pos,
        distance=distance,
        yaw=yaw,
        pitch=pitch,
        roll=0,
        upAxisIndex=2
    )
    proj_matrix = p.computeProjectionMatrixFOV(
        fov=55, aspect=float(width)/float(height), nearVal=0.1, farVal=10.0
    )
    _, _, rgba, _, _ = p.getCameraImage(width, height, view_matrix, proj_matrix, renderer=p.ER_TINY_RENDERER)
    return Image.fromarray(rgba)


def set_steering_angles(rid, fl, fr, rl, rr):
    """Set knuckle steering angles in radians."""
    joint_map = {}
    for i in range(p.getNumJoints(rid)):
        info = p.getJointInfo(rid, i)
        jname = info[1].decode('utf-8')
        joint_map[jname] = i

    for name, angle in [
        ('fl_steering_joint', fl),
        ('fr_steering_joint', fr),
        ('rl_steering_joint', rl),
        ('rr_steering_joint', rr)
    ]:
        if name in joint_map:
            p.resetJointState(rid, joint_map[name], angle)


def main():
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"
    urdf_path = os.path.join(ws_root, "urdf", "robot.urdf")
    shots_dir = os.path.join(ws_root, "screenshots")
    artifact_dir = "/home/bumble/.gemini/antigravity/brain/eb11fa95-96d2-46db-80ff-1f4e563c69c3"
    os.makedirs(shots_dir, exist_ok=True)

    print("Generating 3D Robot Visualizations...")
    cid = setup_pybullet()
    rid = p.loadURDF(urdf_path)

    # 1. Isometric 3D (Neutral pose)
    set_steering_angles(rid, 0, 0, 0, 0)
    img_iso = render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25)
    path_iso = os.path.join(shots_dir, "robot_isometric_3d.png")
    img_iso.save(path_iso)
    img_iso.save(os.path.join(artifact_dir, "robot_isometric_3d.png"))
    print(f" -> Saved: {path_iso}")

    # 2. Top-Down 3D View
    img_top = render_view(rid, [0, 0, 0.10], distance=1.1, yaw=0, pitch=-89)
    path_top = os.path.join(shots_dir, "robot_top_3d.png")
    img_top.save(path_top)
    img_top.save(os.path.join(artifact_dir, "robot_top_3d.png"))
    print(f" -> Saved: {path_top}")

    # 3. Front Perspective 3D View
    img_front = render_view(rid, [0, 0, 0.12], distance=1.0, yaw=0, pitch=-10)
    path_front = os.path.join(shots_dir, "robot_front_3d.png")
    img_front.save(path_front)
    img_front.save(os.path.join(artifact_dir, "robot_front_3d.png"))
    print(f" -> Saved: {path_front}")

    # 4. Side Profile 3D View
    img_side = render_view(rid, [0, 0, 0.12], distance=1.0, yaw=90, pitch=-10)
    path_side = os.path.join(shots_dir, "robot_side_3d.png")
    img_side.save(path_side)
    img_side.save(os.path.join(artifact_dir, "robot_side_3d.png"))
    print(f" -> Saved: {path_side}")

    # 5. Steering Demonstration: Mode B (4WS Counter-phase)
    set_steering_angles(rid, math.radians(25), math.radians(25), -math.radians(25), -math.radians(25))
    img_counter = render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25)
    path_counter = os.path.join(shots_dir, "robot_steering_counterphase.png")
    img_counter.save(path_counter)
    img_counter.save(os.path.join(artifact_dir, "robot_steering_counterphase.png"))
    print(f" -> Saved: {path_counter}")

    # 6. Steering Demonstration: Mode C (Crab Parallel)
    set_steering_angles(rid, math.radians(35), math.radians(35), math.radians(35), math.radians(35))
    img_crab = render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25)
    path_crab = os.path.join(shots_dir, "robot_steering_crab.png")
    img_crab.save(path_crab)
    img_crab.save(os.path.join(artifact_dir, "robot_steering_crab.png"))
    print(f" -> Saved: {path_crab}")

    # 7. Steering Demonstration: Mode E (Rotation in Place)
    set_steering_angles(rid, -math.radians(45), math.radians(45), math.radians(45), -math.radians(45))
    img_inplace = render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25)
    path_inplace = os.path.join(shots_dir, "robot_steering_inplace.png")
    img_inplace.save(path_inplace)
    img_inplace.save(os.path.join(artifact_dir, "robot_steering_inplace.png"))
    print(f" -> Saved: {path_inplace}")

    p.disconnect()
    print("All 3D Robot Visualizations successfully generated!")


if __name__ == '__main__':
    main()

