#!/usr/bin/env python3
"""
Export 2D SLAM Arena Map to YAML, PGM, and PNG format for Four-Wheel Steering Robot.
"""

import os
import math
import numpy as np
from PIL import Image

def generate_arena_map():
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"
    maps_dir = os.path.join(ws_root, "maps")
    os.makedirs(maps_dir, exist_ok=True)

    resolution = 0.05  # 5cm/cell
    width = 220        # 11m span
    height = 220       # 11m span
    origin_x = -5.5
    origin_y = -5.5

    # 254 = free, 0 = occupied, 205 = unknown
    grid = np.full((height, width), 254, dtype=np.uint8)

    # Walls and bounds
    # Arena bounds: -5.0 to 5.0
    for y_idx in range(height):
        for x_idx in range(width):
            wx = origin_x + x_idx * resolution
            wy = origin_y + y_idx * resolution

            # Outside 10x10 arena is unknown
            if abs(wx) > 5.1 or abs(wy) > 5.1:
                grid[y_idx, x_idx] = 205
            # Outer walls (thickness 0.2m)
            elif (abs(wx) >= 4.9 and abs(wx) <= 5.1) or (abs(wy) >= 4.9 and abs(wy) <= 5.1):
                grid[y_idx, x_idx] = 0

    # Internal obstacles:
    # 1. pillar_northeast: center (2.5, 2.2), radius 0.4
    # 2. box_northwest: center (-2.2, 2.2), size 0.8x0.8
    # 3. pillar_southeast: center (2.5, -2.2), radius 0.4
    # 4. partition_southwest: center (-2.2, -2.2), size 0.2x1.8
    # 5. center_barrier: center (0.0, 0.0), size 1.5x0.2
    for y_idx in range(height):
        for x_idx in range(width):
            wx = origin_x + x_idx * resolution
            wy = origin_y + y_idx * resolution

            # Northeast pillar (radius 0.4m)
            if math.hypot(wx - 2.5, wy - 2.2) <= 0.40:
                grid[y_idx, x_idx] = 0

            # Northwest box (0.8m x 0.8m)
            if abs(wx - (-2.2)) <= 0.40 and abs(wy - 2.2) <= 0.40:
                grid[y_idx, x_idx] = 0

            # Southeast pillar (radius 0.4m)
            if math.hypot(wx - 2.5, wy - (-2.2)) <= 0.40:
                grid[y_idx, x_idx] = 0

            # Southwest wall partition (0.2m x 1.8m)
            if abs(wx - (-2.2)) <= 0.10 and abs(wy - (-2.2)) <= 0.90:
                grid[y_idx, x_idx] = 0

            # Central divider (1.5m x 0.2m)
            if abs(wx - 0.0) <= 0.75 and abs(wy - 0.0) <= 0.10:
                grid[y_idx, x_idx] = 0

    # Flip vertically for ROS PGM format convention (origin lower-left)
    pgm_data = np.flipud(grid)

    pgm_path = os.path.join(maps_dir, "four_wheel_arena_map.pgm")
    yaml_path = os.path.join(maps_dir, "four_wheel_arena_map.yaml")
    png_path = os.path.join(maps_dir, "four_wheel_arena_map.png")

    # Write PGM
    with open(pgm_path, 'wb') as f:
        header = f"P5\n{width} {height}\n255\n".encode('ascii')
        f.write(header)
        f.write(pgm_data.tobytes())

    # Write YAML
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

    # Save PNG
    im = Image.fromarray(pgm_data)
    im.save(png_path)

    print(f"Generated: {pgm_path}")
    print(f"Generated: {yaml_path}")
    print(f"Generated: {png_path}")

if __name__ == '__main__':
    generate_arena_map()

