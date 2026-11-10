#!/usr/bin/env python3
"""
Frontier Detection and Exploration Planning Engine for Four-Wheel Steering Robot.

Implements:
1. Fast 8-connected frontier cell detection on nav_msgs/OccupancyGrid.
2. Obstacle clearance estimation via Euclidean Distance Transforms.
3. Connected-component clustering of contiguous frontier cells.
4. Safe representative goal projection into verified collision-free space.
5. Utility ranking balancing travel distance, frontier size, and obstacle clearance.
6. Temporal spatial blacklisting for failed or unreachable goals.
"""

import math
import os
os.environ.setdefault('PYTHONNOUSERSITE', '1')

import collections
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np
from scipy import ndimage


@dataclass
class FrontierGoal:
    """Represents a validated, ranked exploration destination in world coordinates."""
    x: float
    y: float
    yaw: float
    cluster_size: int
    obstacle_distance: float
    distance_to_robot: float = 0.0
    cost: float = 0.0
    grid_x: int = 0
    grid_y: int = 0


@dataclass
class FrontierCluster:
    """Represents a grouped cluster of frontier cells."""
    cells: List[Tuple[int, int]]
    size: int
    centroid_grid: Tuple[float, float]
    unknown_neighbors: List[Tuple[int, int]] = field(default_factory=list)
    goal: Optional[FrontierGoal] = None


@dataclass
class BlacklistEntry:
    """Records a failed destination and its suppression window."""
    x: float
    y: float
    added_time: float
    expiry_time: float
    failure_count: int = 1


def quaternion_to_yaw(q) -> float:
    """Extract 2D yaw angle from geometry_msgs/Quaternion or object with x,y,z,w."""
    if hasattr(q, 'x'):
        qx, qy, qz, qw = q.x, q.y, q.z, q.w
    elif isinstance(q, (list, tuple)) and len(q) == 4:
        qx, qy, qz, qw = q[0], q[1], q[2], q[3]
    else:
        return 0.0
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.atan2(siny_cosp, cosy_cosp)


class FrontierDetector:
    """
    Modular, high-performance frontier extraction and goal selection engine.
    Independent of ROS middleware for complete standalone testability.
    """

    def __init__(
        self,
        min_cluster_size: int = 5,
        obstacle_safety_distance: float = 0.32,
        min_distance_to_goal: float = 0.50,
        max_distance_to_goal: float = 12.0,
        weight_distance: float = 1.0,
        weight_size: float = 0.05,
        weight_clearance: float = 0.20,
        blacklist_radius: float = 0.60,
        blacklist_duration: float = 60.0,
        free_threshold: int = 25,
        occupied_threshold: int = 50,
        max_workspace_radius: float = 0.0  # 0.0 means unconstrained
    ):
        self.min_cluster_size = min_cluster_size
        self.obstacle_safety_distance = obstacle_safety_distance
        self.min_distance_to_goal = min_distance_to_goal
        self.max_distance_to_goal = max_distance_to_goal
        self.weight_distance = weight_distance
        self.weight_size = weight_size
        self.weight_clearance = weight_clearance
        self.blacklist_radius = blacklist_radius
        self.blacklist_duration = blacklist_duration
        self.free_threshold = free_threshold
        self.occupied_threshold = occupied_threshold
        self.max_workspace_radius = max_workspace_radius

        self.blacklist: List[BlacklistEntry] = []

    def grid_to_world(
        self,
        gx: float,
        gy: float,
        origin_x: float,
        origin_y: float,
        resolution: float,
        origin_yaw: float = 0.0
    ) -> Tuple[float, float]:
        """Convert continuous/discrete grid coordinates to global world frame coordinates."""
        dx = (gx + 0.5) * resolution
        dy = (gy + 0.5) * resolution
        cos_yaw = math.cos(origin_yaw)
        sin_yaw = math.sin(origin_yaw)
        wx = origin_x + (cos_yaw * dx - sin_yaw * dy)
        wy = origin_y + (sin_yaw * dx + cos_yaw * dy)
        return wx, wy

    def world_to_grid(
        self,
        wx: float,
        wy: float,
        origin_x: float,
        origin_y: float,
        resolution: float,
        origin_yaw: float = 0.0
    ) -> Tuple[int, int]:
        """Convert global world coordinates to discrete grid cell indices."""
        dx = wx - origin_x
        dy = wy - origin_y
        cos_yaw = math.cos(-origin_yaw)
        sin_yaw = math.sin(-origin_yaw)
        gx = int(math.floor((cos_yaw * dx - sin_yaw * dy) / resolution))
        gy = int(math.floor((sin_yaw * dx + cos_yaw * dy) / resolution))
        return gx, gy

    def is_blacklisted(self, x: float, y: float, current_time: float) -> bool:
        """Check if a world coordinate falls within any active blacklist radius."""
        for entry in self.blacklist:
            if current_time <= entry.expiry_time:
                dist = math.hypot(x - entry.x, y - entry.y)
                if dist <= self.blacklist_radius:
                    return True
        return False

    def add_to_blacklist(self, x: float, y: float, current_time: float):
        """Register a destination into the blacklist or extend existing nearby entry."""
        for entry in self.blacklist:
            if math.hypot(x - entry.x, y - entry.y) <= self.blacklist_radius:
                entry.expiry_time = current_time + self.blacklist_duration * (entry.failure_count + 1)
                entry.failure_count += 1
                return

        self.blacklist.append(
            BlacklistEntry(
                x=x,
                y=y,
                added_time=current_time,
                expiry_time=current_time + self.blacklist_duration,
                failure_count=1
            )
        )

    def prune_blacklist(self, current_time: float):
        """Purge expired blacklist entries."""
        self.blacklist = [e for e in self.blacklist if current_time <= e.expiry_time]

    def clear_blacklist(self):
        """Manually clear the blacklist."""
        self.blacklist.clear()

    def parse_occupancy_grid(self, grid_msg) -> Optional[Tuple[np.ndarray, float, float, float, float]]:
        """Extract numpy 2D array and metadata from nav_msgs/OccupancyGrid or dict."""
        if grid_msg is None:
            return None

        if hasattr(grid_msg, 'info') and hasattr(grid_msg, 'data'):
            width = grid_msg.info.width
            height = grid_msg.info.height
            resolution = grid_msg.info.resolution
            origin_x = grid_msg.info.origin.position.x
            origin_y = grid_msg.info.origin.position.y
            origin_yaw = quaternion_to_yaw(grid_msg.info.origin.orientation)
            data = grid_msg.data
        elif isinstance(grid_msg, dict):
            width = grid_msg.get('width', 0)
            height = grid_msg.get('height', 0)
            resolution = grid_msg.get('resolution', 0.05)
            origin_x = grid_msg.get('origin_x', 0.0)
            origin_y = grid_msg.get('origin_y', 0.0)
            origin_yaw = grid_msg.get('origin_yaw', 0.0)
            data = grid_msg.get('data', [])
        else:
            return None

        if width <= 0 or height <= 0 or len(data) != width * height:
            return None

        grid = np.array(data, dtype=np.int8).reshape((height, width))
        return grid, resolution, origin_x, origin_y, origin_yaw

    def find_frontiers(self, grid: np.ndarray) -> np.ndarray:
        """
        Identify frontier cells in the occupancy grid.
        A frontier cell is known free space (0 <= cell <= free_threshold)
        adjacent (8-connected) to at least one unknown cell (cell == -1).
        """
        height, width = grid.shape
        free_mask = (grid >= 0) & (grid <= self.free_threshold)
        unknown_mask = (grid == -1)

        struct_8 = ndimage.generate_binary_structure(2, 2)
        unknown_dilated = ndimage.binary_dilation(unknown_mask, structure=struct_8)

        frontier_mask = free_mask & unknown_dilated

        # Clear border cells
        frontier_mask[0, :] = False
        frontier_mask[-1, :] = False
        frontier_mask[:, 0] = False
        frontier_mask[:, -1] = False

        return frontier_mask

    def cluster_frontiers(
        self,
        frontier_mask: np.ndarray,
        grid: np.ndarray
    ) -> List[FrontierCluster]:
        """Cluster 8-connected neighbouring frontier cells using connected components."""
        struct_8 = ndimage.generate_binary_structure(2, 2)
        labeled_array, num_features = ndimage.label(frontier_mask, structure=struct_8)

        if num_features == 0:
            return []

        clusters: List[FrontierCluster] = []
        for cluster_id in range(1, num_features + 1):
            y_coords, x_coords = np.where(labeled_array == cluster_id)
            size = len(x_coords)
            if size < self.min_cluster_size:
                continue

            cells = list(zip(x_coords.tolist(), y_coords.tolist()))
            centroid_x = float(np.mean(x_coords))
            centroid_y = float(np.mean(y_coords))

            clusters.append(
                FrontierCluster(
                    cells=cells,
                    size=size,
                    centroid_grid=(centroid_x, centroid_y)
                )
            )

        return clusters

    def compute_distance_transform(self, grid: np.ndarray, resolution: float) -> np.ndarray:
        """Compute Euclidean distance to nearest obstacle for each cell (in meters)."""
        obstacle_mask = (grid >= self.occupied_threshold)
        if not np.any(obstacle_mask):
            return np.full(grid.shape, 10.0, dtype=np.float32)

        free_or_unknown = ~obstacle_mask
        dist_cells = ndimage.distance_transform_edt(free_or_unknown)
        return dist_cells * resolution

    def extract_safe_goal(
        self,
        cluster: FrontierCluster,
        grid: np.ndarray,
        dist_transform: np.ndarray,
        resolution: float,
        origin_x: float,
        origin_y: float,
        origin_yaw: float = 0.0
    ) -> Optional[FrontierGoal]:
        """Extract a safe representative navigation goal for a frontier cluster."""
        free_mask = (grid >= 0) & (grid <= self.free_threshold)
        safe_mask = free_mask & (dist_transform >= self.obstacle_safety_distance)

        cx, cy = cluster.centroid_grid

        # 1. Search cluster cells with sufficient clearance
        candidates = []
        for gx, gy in cluster.cells:
            if safe_mask[gy, gx]:
                dist_to_c = math.hypot(gx - cx, gy - cy)
                candidates.append((dist_to_c, -dist_transform[gy, gx], gx, gy))

        best_gx, best_gy = None, None
        if candidates:
            candidates.sort()
            _, _, best_gx, best_gy = candidates[0]
        else:
            # 2. Local BFS inward from centroid into verified safe free space
            center_ix, center_iy = int(round(cx)), int(round(cy))
            h, w = grid.shape
            queue = collections.deque([(center_ix, center_iy, 0)])
            visited = {(center_ix, center_iy)}
            found = False

            while queue and not found:
                curr_x, curr_y, dist_step = queue.popleft()
                if dist_step > 25:
                    break

                if 0 <= curr_x < w and 0 <= curr_y < h:
                    if safe_mask[curr_y, curr_x]:
                        best_gx, best_gy = curr_x, curr_y
                        found = True
                        break

                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,-1), (-1,1), (1,1)]:
                    nx, ny = curr_x + dx, curr_y + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny, dist_step + 1))

        if best_gx is None or best_gy is None:
            return None

        # Convert to world coordinates
        wx, wy = self.grid_to_world(best_gx, best_gy, origin_x, origin_y, resolution, origin_yaw)

        # Enforce workspace boundaries if configured (>0)
        if self.max_workspace_radius > 0.0:
            if math.hypot(wx, wy) > self.max_workspace_radius:
                return None

        # Compute heading facing toward unexplored centroid direction
        yaw = math.atan2(cy - best_gy, cx - best_gx) if math.hypot(cx - best_gx, cy - best_gy) > 0.1 else 0.0
        clearance = float(dist_transform[best_gy, best_gx])

        return FrontierGoal(
            x=wx,
            y=wy,
            yaw=yaw,
            cluster_size=cluster.size,
            obstacle_distance=clearance,
            grid_x=best_gx,
            grid_y=best_gy
        )

    def rank_goals(
        self,
        goals: List[FrontierGoal],
        robot_x: float,
        robot_y: float,
        robot_yaw: float = 0.0,
        current_time: float = 0.0
    ) -> List[FrontierGoal]:
        """Rank candidate goals using cost balancing distance, cluster size, and obstacle clearance."""
        self.prune_blacklist(current_time)
        valid_goals = []

        for goal in goals:
            if self.is_blacklisted(goal.x, goal.y, current_time):
                continue

            dist = math.hypot(goal.x - robot_x, goal.y - robot_y)
            if dist < self.min_distance_to_goal or dist > self.max_distance_to_goal:
                continue

            goal.distance_to_robot = dist

            # Heading difference penalty
            angle_to_goal = math.atan2(goal.y - robot_y, goal.x - robot_x)
            heading_diff = abs(math.atan2(math.sin(angle_to_goal - robot_yaw), math.cos(angle_to_goal - robot_yaw)))

            # Cost function: lower is better
            cost = (
                self.weight_distance * dist
                - self.weight_size * min(goal.cluster_size, 100)
                - self.weight_clearance * min(goal.obstacle_distance, 1.0)
                + 0.15 * heading_diff
            )
            goal.cost = cost
            valid_goals.append(goal)

        valid_goals.sort(key=lambda g: g.cost)
        return valid_goals

    def plan_exploration_goals(
        self,
        grid_msg,
        robot_x: float,
        robot_y: float,
        robot_yaw: float = 0.0,
        current_time: float = 0.0
    ) -> Tuple[List[FrontierGoal], List[FrontierCluster]]:
        """Complete exploration pipeline: parse -> detect -> cluster -> validate -> rank."""
        parsed = self.parse_occupancy_grid(grid_msg)
        if parsed is None:
            return [], []

        grid, resolution, origin_x, origin_y, origin_yaw = parsed
        frontier_mask = self.find_frontiers(grid)
        clusters = self.cluster_frontiers(frontier_mask, grid)

        if not clusters:
            return [], []

        dist_transform = self.compute_distance_transform(grid, resolution)

        candidate_goals: List[FrontierGoal] = []
        for cluster in clusters:
            goal = self.extract_safe_goal(
                cluster, grid, dist_transform, resolution, origin_x, origin_y, origin_yaw
            )
            if goal is not None:
                cluster.goal = goal
                candidate_goals.append(goal)

        ranked_goals = self.rank_goals(candidate_goals, robot_x, robot_y, robot_yaw, current_time)
        return ranked_goals, clusters

