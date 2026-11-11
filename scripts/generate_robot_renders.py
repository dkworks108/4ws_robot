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
    ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    urdf_path = os.path.join(ws_root, "urdf", "robot.urdf")
    shots_dir = os.path.join(ws_root, "screenshots")
    artifact_dir = os.environ.get("SCREENSHOT_ARTIFACT_DIR", "")
    os.makedirs(shots_dir, exist_ok=True)
    if artifact_dir:
        os.makedirs(artifact_dir, exist_ok=True)

    def save_render(img, filename):
        path = os.path.join(shots_dir, filename)
        img.save(path)
        if artifact_dir:
            img.save(os.path.join(artifact_dir, filename))
        print(f" -> Saved: {path}")

    print("Generating 3D Robot Visualizations...")
    cid = setup_pybullet()
    rid = p.loadURDF(urdf_path)

    # 1. Isometric 3D (Neutral pose)
    set_steering_angles(rid, 0, 0, 0, 0)
    save_render(render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25), "robot_isometric_3d.png")

    # 2. Top-Down 3D View
    save_render(render_view(rid, [0, 0, 0.10], distance=1.1, yaw=0, pitch=-89), "robot_top_3d.png")

    # 3. Front Perspective 3D View
    save_render(render_view(rid, [0, 0, 0.12], distance=1.0, yaw=0, pitch=-10), "robot_front_3d.png")

    # 4. Side Profile 3D View
    save_render(render_view(rid, [0, 0, 0.12], distance=1.0, yaw=90, pitch=-10), "robot_side_3d.png")

    # 5. Steering Demonstration: Mode B (4WS Counter-phase)
    set_steering_angles(rid, math.radians(25), math.radians(25), -math.radians(25), -math.radians(25))
    save_render(render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25), "robot_steering_counterphase.png")

    # 6. Steering Demonstration: Mode C (Crab Parallel)
    set_steering_angles(rid, math.radians(35), math.radians(35), math.radians(35), math.radians(35))
    save_render(render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25), "robot_steering_crab.png")

    # 7. Steering Demonstration: Mode E (Rotation in Place)
    set_steering_angles(rid, -math.radians(45), math.radians(45), math.radians(45), -math.radians(45))
    save_render(render_view(rid, [0, 0, 0.12], distance=1.1, yaw=45, pitch=-25), "robot_steering_inplace.png")

    p.disconnect()
    print("All 3D Robot Visualizations successfully generated!")


if __name__ == '__main__':
    main()

