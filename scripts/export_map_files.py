#!/usr/bin/env python3
"""
Export 2D SLAM Arena & Outdoor Proving Ground Maps to YAML, PGM, and PNG format.
"""

import os
import math
import shutil
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

def generate_arena_map(maps_dir: str):
    """Generate 10x10m arena map."""
    resolution = 0.05  # 5cm/cell
    width = 220        # 11m span
    height = 220       # 11m span
    origin_x = -5.5
    origin_y = -5.5

    # 254 = free, 0 = occupied, 205 = unknown
    grid = np.full((height, width), 254, dtype=np.uint8)

    for y_idx in range(height):
        for x_idx in range(width):
            wx = origin_x + x_idx * resolution
            wy = origin_y + y_idx * resolution

            if abs(wx) > 5.1 or abs(wy) > 5.1:
                grid[y_idx, x_idx] = 205
            elif (abs(wx) >= 4.9 and abs(wx) <= 5.1) or (abs(wy) >= 4.9 and abs(wy) <= 5.1):
                grid[y_idx, x_idx] = 0

            # Northeast pillar
            if math.hypot(wx - 2.5, wy - 2.2) <= 0.40:
                grid[y_idx, x_idx] = 0
            # Northwest box
            if abs(wx - (-2.2)) <= 0.40 and abs(wy - 2.2) <= 0.40:
                grid[y_idx, x_idx] = 0
            # Southeast pillar
            if math.hypot(wx - 2.5, wy - (-2.2)) <= 0.40:
                grid[y_idx, x_idx] = 0
            # Southwest wall partition
            if abs(wx - (-2.2)) <= 0.10 and abs(wy - (-2.2)) <= 0.90:
                grid[y_idx, x_idx] = 0
            # Central divider
            if abs(wx - 0.0) <= 0.75 and abs(wy - 0.0) <= 0.10:
                grid[y_idx, x_idx] = 0

    pgm_data = np.flipud(grid)
    pgm_path = os.path.join(maps_dir, "four_wheel_arena_map.pgm")
    yaml_path = os.path.join(maps_dir, "four_wheel_arena_map.yaml")
    png_path = os.path.join(maps_dir, "four_wheel_arena_map.png")

    with open(pgm_path, 'wb') as f:
        header = f"P5\n{width} {height}\n255\n".encode('ascii')
        f.write(header)
        f.write(pgm_data.tobytes())

    yaml_content = f"""image: four_wheel_arena_map.pgm
mode: trinary
resolution: {resolution}
origin: [{origin_x}, {origin_y}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    im = Image.fromarray(pgm_data)
    im.save(png_path)
    print(f"Generated: {pgm_path}")


def generate_proving_ground_map(sdf_path: str, maps_dir: str):
    """Generate 65x65m outdoor proving ground tactical map from SDF."""
    tree = ET.parse(sdf_path)
    root = tree.getroot()
    world = root.find('world')

    resolution = 0.10  # 10cm/cell for wide 65x65m map
    span = 66.0
    width = int(span / resolution)
    height = int(span / resolution)
    origin_x = -span / 2.0
    origin_y = -span / 2.0

    # 254 = free space, 0 = obstacle, 205 = unknown
    grid = np.full((height, width), 254, dtype=np.uint8)

    # Outside perimeter (> 30.5m) is unknown
    for y_idx in range(height):
        for x_idx in range(width):
            wx = origin_x + x_idx * resolution
            wy = origin_y + y_idx * resolution
            if abs(wx) > 30.5 or abs(wy) > 30.5:
                grid[y_idx, x_idx] = 205

    for model in world.findall('model'):
        name = model.attrib.get('name', '')
        if name in ['terrain_ground']:
            continue

        pose_elem = model.find('pose')
        if pose_elem is None or not pose_elem.text:
            continue
        parts = [float(x) for x in pose_elem.text.strip().split()]
        mx, my = parts[0], parts[1]
        m_yaw = parts[5] if len(parts) > 5 else 0.0

        # Check box geometries
        for box in model.findall('.//geometry/box/size'):
            bs = [float(x) for x in box.text.strip().split()]
            bw, bl = bs[0], bs[1]

            # Bounding check
            x_min = int((mx - max(bw, bl) - origin_x) / resolution)
            x_max = int((mx + max(bw, bl) - origin_x) / resolution) + 1
            y_min = int((my - max(bw, bl) - origin_y) / resolution)
            y_max = int((my + max(bw, bl) - origin_y) / resolution) + 1

            for y_idx in range(max(0, y_min), min(height, y_max)):
                for x_idx in range(max(0, x_min), min(width, x_max)):
                    wx = origin_x + x_idx * resolution
                    wy = origin_y + y_idx * resolution

                    dx = wx - mx
                    dy = wy - my
                    if m_yaw != 0.0:
                        cos_y = math.cos(-m_yaw)
                        sin_y = math.sin(-m_yaw)
                        rx = dx * cos_y - dy * sin_y
                        ry = dx * sin_y + dy * cos_y
                    else:
                        rx, ry = dx, dy

                    if abs(rx) <= (bw / 2.0 + 0.05) and abs(ry) <= (bl / 2.0 + 0.05):
                        grid[y_idx, x_idx] = 0

        # Check cylinder geometries
        for cyl in model.findall('.//geometry/cylinder/radius'):
            r = float(cyl.text.strip())
            x_min = int((mx - r - origin_x) / resolution)
            x_max = int((mx + r - origin_x) / resolution) + 1
            y_min = int((my - r - origin_y) / resolution)
            y_max = int((my + r - origin_y) / resolution) + 1

            for y_idx in range(max(0, y_min), min(height, y_max)):
                for x_idx in range(max(0, x_min), min(width, x_max)):
                    wx = origin_x + x_idx * resolution
                    wy = origin_y + y_idx * resolution
                    if math.hypot(wx - mx, wy - my) <= (r + 0.05):
                        grid[y_idx, x_idx] = 0

    pgm_data = np.flipud(grid)
    pgm_path = os.path.join(maps_dir, "outdoor_proving_ground_map.pgm")
    yaml_path = os.path.join(maps_dir, "outdoor_proving_ground_map.yaml")
    png_path = os.path.join(maps_dir, "outdoor_proving_ground_map.png")

    with open(pgm_path, 'wb') as f:
        header = f"P5\n{width} {height}\n255\n".encode('ascii')
        f.write(header)
        f.write(pgm_data.tobytes())

    yaml_content = f"""image: outdoor_proving_ground_map.pgm
mode: trinary
resolution: {resolution}
origin: [{origin_x}, {origin_y}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    im = Image.fromarray(pgm_data)
    im.save(png_path)
    print(f"Generated: {pgm_path}")
    print(f"Generated: {yaml_path}")
    print(f"Generated: {png_path}")


def main():
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"
    sdf_path = os.path.join(ws_root, "worlds", "outdoor_proving_ground.sdf")
    maps_dir = os.path.join(ws_root, "maps")
    artifact_dir = "/home/bumble/.gemini/antigravity/brain/eb11fa95-96d2-46db-80ff-1f4e563c69c3"
    
    os.makedirs(maps_dir, exist_ok=True)
    os.makedirs(artifact_dir, exist_ok=True)

    print("Exporting maps...")
    generate_arena_map(maps_dir)
    generate_proving_ground_map(sdf_path, maps_dir)

    # Copy to artifacts
    for f in ["outdoor_proving_ground_map.png", "four_wheel_arena_map.png"]:
        src = os.path.join(maps_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(artifact_dir, f))

    print("Map export complete!")

if __name__ == '__main__':
    main()
