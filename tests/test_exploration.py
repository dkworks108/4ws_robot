#!/usr/bin/env python3
"""
Unit tests for Frontier Detection and Exploration Planning Engine.
"""

import os
import sys
import math
import numpy as np
import pytest

WS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WS_ROOT, 'src', 'four_wheel_exploration'))
sys.path.insert(0, os.path.join(WS_ROOT, 'src', 'four_wheel_control'))

from four_wheel_exploration.frontier_detector import FrontierDetector, FrontierCluster, FrontierGoal


@pytest.fixture
def detector():
    return FrontierDetector(
        min_cluster_size=4,
        obstacle_safety_distance=0.30,
        min_distance_to_goal=0.50,
        max_distance_to_goal=12.0,
        blacklist_radius=0.60,
        blacklist_duration=30.0,
        free_threshold=25,
        occupied_threshold=50,
        max_workspace_radius=0.0
    )


def create_synthetic_map(width=60, height=60, resolution=0.05):
    """
    Creates a synthetic occupancy grid:
    - Inner 30x30 is free space (0)
    - Outer is unknown (-1)
    - Border between free and unknown constitutes frontiers!
    - Obstacle column at (10, 10) to (15, 15) (100)
    """
    grid = np.full((height, width), -1, dtype=np.int8)
    # Free space in center [15:45, 15:45]
    grid[15:45, 15:45] = 0
    # Add an obstacle box inside free space
    grid[20:25, 20:25] = 100

    origin_x = - (width * resolution) / 2.0
    origin_y = - (height * resolution) / 2.0

    return {
        'width': width,
        'height': height,
        'resolution': resolution,
        'origin_x': origin_x,
        'origin_y': origin_y,
        'origin_yaw': 0.0,
        'data': grid.flatten().tolist()
    }


def test_frontier_detection(detector):
    synth_map = create_synthetic_map()
    parsed = detector.parse_occupancy_grid(synth_map)
    assert parsed is not None
    grid, res, ox, oy, oyaw = parsed

    frontier_mask = detector.find_frontiers(grid)
    assert np.any(frontier_mask), "Should detect frontier cells on the free-unknown border"
    # Free space center should not be frontier
    assert not frontier_mask[30, 30], "Center of free space should not be a frontier"


def test_clustering_and_filtering(detector):
    synth_map = create_synthetic_map()
    parsed = detector.parse_occupancy_grid(synth_map)
    grid, res, ox, oy, oyaw = parsed

    frontier_mask = detector.find_frontiers(grid)
    clusters = detector.cluster_frontiers(frontier_mask, grid)

    assert len(clusters) > 0, f"Expected clusters, got {len(clusters)}"
    for c in clusters:
        assert c.size >= detector.min_cluster_size, f"Cluster size {c.size} below minimum {detector.min_cluster_size}"


def test_safe_goal_extraction(detector):
    synth_map = create_synthetic_map()
    parsed = detector.parse_occupancy_grid(synth_map)
    grid, res, ox, oy, oyaw = parsed

    frontier_mask = detector.find_frontiers(grid)
    clusters = detector.cluster_frontiers(frontier_mask, grid)
    dist_transform = detector.compute_distance_transform(grid, res)

    goals = []
    for c in clusters:
        goal = detector.extract_safe_goal(c, grid, dist_transform, res, ox, oy, oyaw)
        if goal:
            goals.append(goal)

    assert len(goals) > 0, "Should extract at least one safe goal"
    for g in goals:
        assert g.obstacle_distance >= detector.obstacle_safety_distance - 1e-4, (
            f"Goal clearance {g.obstacle_distance} below safe limit {detector.obstacle_safety_distance}"
        )


def test_goal_ranking_and_blacklisting(detector):
    synth_map = create_synthetic_map()
    goals, clusters = detector.plan_exploration_goals(
        synth_map, robot_x=0.0, robot_y=0.0, current_time=10.0
    )

    assert len(goals) > 0
    top_goal = goals[0]

    # Verify blacklisting
    detector.add_to_blacklist(top_goal.x, top_goal.y, current_time=10.0)
    assert detector.is_blacklisted(top_goal.x, top_goal.y, current_time=10.0)

    # Next ranking should exclude or downrank blacklisted goal
    new_goals, _ = detector.plan_exploration_goals(
        synth_map, robot_x=0.0, robot_y=0.0, current_time=10.0
    )
    if new_goals:
        assert (new_goals[0].x, new_goals[0].y) != (top_goal.x, top_goal.y)

    # Expiry check
    detector.prune_blacklist(current_time=50.0)
    assert not detector.is_blacklisted(top_goal.x, top_goal.y, current_time=50.0)


if __name__ == '__main__':
    pytest.main(['-v', __file__])
