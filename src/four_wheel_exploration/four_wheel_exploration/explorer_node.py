#!/usr/bin/env python3
"""
Autonomous Frontier Exploration ROS 2 Node for Four-Wheel Steering Robot.

Coordinates:
- Multi-criteria frontier extraction and sector-balanced goal dispatch.
- Real-time map coverage tracking and telemetry publishing.
- Nav2 NavigateToPose action client with progress monitoring and stall detection.
- Dynamic temporary blacklisting with auto-unblacklist recovery.
- RViz visualization markers (frontiers, centroids, and active goals).
- Clean node shutdown.
"""

import json
import math
import os
import sys

# Ensure clean system-site packages without NumPy 1.x / 2.x conflicts
sys.path = [p for p in sys.path if not ('.local' in p and 'site-packages' in p)]
os.environ.setdefault('PYTHONNOUSERSITE', '1')

from typing import Optional, Tuple, List, Dict

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.time import Time

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import String, ColorRGBA
from std_srvs.srv import Trigger

from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus

import tf2_ros
from tf2_ros import Buffer, TransformListener

from four_wheel_exploration.frontier_detector import FrontierDetector, FrontierGoal, quaternion_to_yaw


class FrontierExplorerNode(Node):
    """
    Orchestrates autonomous frontier-based exploration via Nav2 action client.
    Guarantees complete coverage of the outdoor proving ground and all 4 sectors.
    """

    STATE_IDLE = "IDLE"
    STATE_SEARCHING = "SEARCHING_FRONTIERS"
    STATE_NAVIGATING = "NAVIGATING"
    STATE_PAUSED = "PAUSED"
    STATE_RECOVERY = "RECOVERY_CLEARING"
    STATE_COMPLETED = "COMPLETED"

    def __init__(self):
        super().__init__('explorer_node')

        # Parameters
        params = [
            ('min_cluster_size', 4),
            ('obstacle_safety_distance', 0.35),
            ('min_distance_to_goal', 0.40),
            ('max_distance_to_goal', 55.0),
            ('blacklist_radius', 0.60),
            ('blacklist_duration', 30.0),
            ('goal_timeout', 70.0),
            ('max_workspace_radius', 29.0),
            ('exploration_rate', 1.0),
            ('stall_detection_timeout', 25.0),
            ('use_sim_time', True)
        ]
        for name, default_val in params:
            if not self.has_parameter(name):
                self.declare_parameter(name, default_val)

        min_cluster = self.get_parameter('min_cluster_size').value
        safety_dist = self.get_parameter('obstacle_safety_distance').value
        min_dist = self.get_parameter('min_distance_to_goal').value
        max_dist = self.get_parameter('max_distance_to_goal').value
        bl_radius = self.get_parameter('blacklist_radius').value
        bl_duration = self.get_parameter('blacklist_duration').value
        self.goal_timeout = self.get_parameter('goal_timeout').value
        max_ws_radius = self.get_parameter('max_workspace_radius').value
        rate = self.get_parameter('exploration_rate').value
        self.stall_timeout = self.get_parameter('stall_detection_timeout').value

        self.detector = FrontierDetector(
            min_cluster_size=min_cluster,
            obstacle_safety_distance=safety_dist,
            min_distance_to_goal=min_dist,
            max_distance_to_goal=max_dist,
            blacklist_radius=bl_radius,
            blacklist_duration=bl_duration,
            max_workspace_radius=max_ws_radius
        )

        # State tracking
        self.state = self.STATE_IDLE
        self.latest_map: Optional[OccupancyGrid] = None
        self.current_goal: Optional[FrontierGoal] = None
        self.navigation_goal_handle = None
        self.goal_start_time = None
        self.last_progress_time = None
        self.last_distance_remaining = float('inf')
        self.consecutive_failures = 0
        self.goals_completed = 0
        self.recovery_attempts = 0

        # TF Buffer & Listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Nav2 Action Client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Publishers
        self.pub_status = self.create_publisher(String, '/exploration/status', 10)
        self.pub_coverage = self.create_publisher(String, '/exploration/coverage', 10)
        self.pub_markers = self.create_publisher(MarkerArray, '/exploration/frontiers', 10)
        self.pub_goal_marker = self.create_publisher(Marker, '/exploration/current_goal', 10)

        # Subscribers
        self.sub_map = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.cb_map,
            10
        )

        # Services
        self.srv_pause = self.create_service(Trigger, '/exploration/pause', self.cb_pause)
        self.srv_resume = self.create_service(Trigger, '/exploration/resume', self.cb_resume)
        self.srv_stop = self.create_service(Trigger, '/exploration/stop', self.cb_stop)

        # Main Exploration Loop Timer
        self.loop_timer = self.create_timer(1.0 / rate, self.exploration_cycle)

        self.get_logger().info("FrontierExplorerNode (Full-Map Exploration Engine) initialized and ready.")

    def cb_map(self, msg: OccupancyGrid):
        """Receive updated occupancy grid from SLAM."""
        self.latest_map = msg

    def cb_pause(self, request, response):
        """Pause exploration service."""
        if self.state == self.STATE_NAVIGATING and self.navigation_goal_handle:
            self.navigation_goal_handle.cancel_goal_async()
        self.state = self.STATE_PAUSED
        response.success = True
        response.message = "Exploration paused."
        self.get_logger().info("Exploration paused via service.")
        return response

    def cb_resume(self, request, response):
        """Resume exploration service."""
        if self.state in (self.STATE_PAUSED, self.STATE_COMPLETED):
            self.state = self.STATE_SEARCHING
            response.success = True
            response.message = "Exploration resumed."
            self.get_logger().info("Exploration resumed via service.")
        else:
            response.success = False
            response.message = f"Cannot resume from state {self.state}."
        return response

    def cb_stop(self, request, response):
        """Stop exploration service permanently."""
        if self.state == self.STATE_NAVIGATING and self.navigation_goal_handle:
            self.navigation_goal_handle.cancel_goal_async()
        self.state = self.STATE_COMPLETED
        response.success = True
        response.message = "Exploration stopped."
        self.get_logger().info("Exploration stopped via service.")
        return response

    def get_robot_pose(self) -> Optional[Tuple[float, float, float]]:
        """Look up robot pose (x, y, yaw) in 'map' frame using TF2."""
        try:
            t = self.tf_buffer.lookup_transform(
                'map',
                'base_footprint',
                Time(),
                timeout=Duration(seconds=0.2)
            )
            rx = t.transform.translation.x
            ry = t.transform.translation.y
            ryaw = quaternion_to_yaw(t.transform.rotation)
            return rx, ry, ryaw
        except Exception:
            return None

    def exploration_cycle(self):
        """Periodic decision cycle of the exploration state machine."""
        # Publish current state
        self.pub_status.publish(String(data=self.state))

        if self.state == self.STATE_PAUSED or self.state == self.STATE_COMPLETED:
            return

        if self.latest_map is None:
            self.get_logger().debug("Waiting for /map...")
            return

        # Publish map coverage telemetry
        coverage = self.detector.compute_map_coverage(self.latest_map)
        coverage["state"] = self.state
        coverage["goals_completed"] = self.goals_completed
        self.pub_coverage.publish(String(data=json.dumps(coverage)))

        pose = self.get_robot_pose()
        if pose is None:
            self.get_logger().debug("Waiting for TF map -> base_footprint...")
            return

        rx, ry, ryaw = pose
        now_sec = self.get_clock().now().nanoseconds / 1e9

        if self.state in (self.STATE_IDLE, self.STATE_SEARCHING, self.STATE_RECOVERY):
            self.plan_and_dispatch_next_goal(rx, ry, ryaw, now_sec)

        elif self.state == self.STATE_NAVIGATING:
            # Check maximum overall timeout
            if self.goal_start_time is not None:
                elapsed = now_sec - self.goal_start_time
                if elapsed > self.goal_timeout:
                    self.get_logger().warn(f"Goal timed out after {elapsed:.1f}s. Cancelling and blacklisting...")
                    if self.navigation_goal_handle:
                        self.navigation_goal_handle.cancel_goal_async()
                    if self.current_goal:
                        self.detector.add_to_blacklist(self.current_goal.x, self.current_goal.y, now_sec)
                    self.state = self.STATE_SEARCHING
                    self.current_goal = None

    def plan_and_dispatch_next_goal(self, rx: float, ry: float, ryaw: float, now_sec: float):
        """Extract frontiers, rank goals with sector balance, and dispatch top candidate to Nav2."""
        if not self.nav_client.wait_for_server(timeout_sec=0.2):
            self.get_logger().debug("Waiting for Nav2 navigate_to_pose action server...")
            return

        ranked_goals, clusters = self.detector.plan_exploration_goals(
            self.latest_map, rx, ry, ryaw, now_sec
        )

        # Publish visualization markers
        self.publish_frontier_markers(clusters)

        if not ranked_goals:
            self.consecutive_failures += 1

            # Recovery Step 1: If blacklisted goals exist, clear blacklist and re-evaluate
            if self.consecutive_failures == 3 and len(self.detector.blacklist) > 0:
                self.get_logger().info("No open frontiers. Clearing blacklist to re-examine potential paths...")
                self.detector.clear_blacklist()
                self.state = self.STATE_RECOVERY
                return

            # Recovery Step 2: Require 8 consecutive ticks before declaring completion
            if self.consecutive_failures >= 8:
                cov = self.detector.compute_map_coverage(self.latest_map)
                self.get_logger().info(
                    f"No remaining reachable frontiers detected across all sectors! "
                    f"Exploration COMPLETED! Total Map Coverage: {cov['explored_pct']}% ({cov['known_area_m2']} m²)"
                )
                self.state = self.STATE_COMPLETED
                self.clear_goal_marker()
            return

        self.consecutive_failures = 0
        best_goal = ranked_goals[0]
        self.current_goal = best_goal
        self.publish_goal_marker(best_goal)

        # Update sector visit metrics
        if best_goal.sector in self.detector.sector_visit_counts:
            self.detector.sector_visit_counts[best_goal.sector] += 1

        self.get_logger().info(
            f"Dispatching Goal #{self.goals_completed+1} [Sector {best_goal.sector}] -> "
            f"({best_goal.x:.2f}, {best_goal.y:.2f}), dist={best_goal.distance_to_robot:.2f}m, "
            f"size={best_goal.cluster_size}, clearance={best_goal.obstacle_distance:.2f}m"
        )

        # Send action goal to Nav2
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.pose.position.x = best_goal.x
        goal_msg.pose.pose.position.y = best_goal.y
        goal_msg.pose.pose.position.z = 0.0

        # Orientation facing exploration area
        half_yaw = best_goal.yaw * 0.5
        goal_msg.pose.pose.orientation.z = math.sin(half_yaw)
        goal_msg.pose.pose.orientation.w = math.cos(half_yaw)

        self.state = self.STATE_NAVIGATING
        self.goal_start_time = now_sec
        self.last_progress_time = now_sec
        self.last_distance_remaining = best_goal.distance_to_robot

        send_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.cb_navigation_feedback
        )
        send_future.add_done_callback(self.cb_goal_response)

    def cb_goal_response(self, future):
        """Handle response from Nav2 action server."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn("Nav2 rejected exploration goal! Blacklisting...")
            now_sec = self.get_clock().now().nanoseconds / 1e9
            if self.current_goal:
                self.detector.add_to_blacklist(self.current_goal.x, self.current_goal.y, now_sec)
            self.state = self.STATE_SEARCHING
            self.current_goal = None
            return

        self.navigation_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.cb_goal_result)

    def cb_navigation_feedback(self, feedback_msg):
        """Monitor navigation feedback and detect if the robot is stalled."""
        if not hasattr(feedback_msg, 'feedback'):
            return

        fb = feedback_msg.feedback
        now_sec = self.get_clock().now().nanoseconds / 1e9

        if hasattr(fb, 'distance_remaining'):
            dist = fb.distance_remaining
            # If distance decreased noticeably, record progress
            if (self.last_distance_remaining - dist) > 0.20:
                self.last_distance_remaining = dist
                self.last_progress_time = now_sec
            else:
                # Check stall duration
                if self.last_progress_time and (now_sec - self.last_progress_time) > self.stall_timeout:
                    self.get_logger().warn(
                        f"Robot progress stalled for {self.stall_timeout}s. Aborting goal to avoid blockage..."
                    )
                    if self.navigation_goal_handle:
                        self.navigation_goal_handle.cancel_goal_async()
                    if self.current_goal:
                        self.detector.add_to_blacklist(self.current_goal.x, self.current_goal.y, now_sec)
                    self.state = self.STATE_SEARCHING
                    self.current_goal = None

    def cb_goal_result(self, future):
        """Handle final result of navigation goal."""
        result = future.result()
        status = result.status
        now_sec = self.get_clock().now().nanoseconds / 1e9

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.goals_completed += 1
            cov = self.detector.compute_map_coverage(self.latest_map) if self.latest_map else {}
            pct = cov.get('explored_pct', 0.0)
            self.get_logger().info(f"Goal #{self.goals_completed} SUCCEEDED! [Total Map Explored: {pct}%]")
        else:
            self.get_logger().warn(f"Goal FAILED with status {status}. Blacklisting destination...")
            if self.current_goal:
                self.detector.add_to_blacklist(self.current_goal.x, self.current_goal.y, now_sec)

        self.state = self.STATE_SEARCHING
        self.current_goal = None
        self.navigation_goal_handle = None

    def publish_frontier_markers(self, clusters):
        """Publish RViz marker points for all detected frontier clusters."""
        marker_array = MarkerArray()

        # Delete all previous markers
        del_marker = Marker()
        del_marker.action = Marker.DELETEALL
        marker_array.markers.append(del_marker)

        res = self.latest_map.info.resolution
        ox = self.latest_map.info.origin.position.x
        oy = self.latest_map.info.origin.position.y

        for i, cluster in enumerate(clusters[:40]):  # Cap at 40 clusters
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'frontiers'
            marker.id = i + 1
            marker.type = Marker.POINTS
            marker.action = Marker.ADD
            marker.scale.x = res * 0.95
            marker.scale.y = res * 0.95

            # Cyan color for frontiers
            marker.color = ColorRGBA(r=0.0, g=0.9, b=1.0, a=0.85)

            for gx, gy in cluster.cells:
                wx, wy = self.detector.grid_to_world(gx, gy, ox, oy, res)
                p = Point()
                p.x = wx
                p.y = wy
                p.z = 0.05
                marker.points.append(p)

            marker_array.markers.append(marker)

        self.pub_markers.publish(marker_array)

    def publish_goal_marker(self, goal: FrontierGoal):
        """Publish RViz visual marker for currently selected goal."""
        marker = Marker()
        marker.header.frame_id = 'map'
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = 'current_goal'
        marker.id = 999
        marker.type = Marker.ARROW
        marker.action = Marker.ADD

        marker.pose.position.x = goal.x
        marker.pose.position.y = goal.y
        marker.pose.position.z = 0.20

        half_yaw = goal.yaw * 0.5
        marker.pose.orientation.z = math.sin(half_yaw)
        marker.pose.orientation.w = math.cos(half_yaw)

        marker.scale.x = 0.50  # length
        marker.scale.y = 0.10  # width
        marker.scale.z = 0.10  # height

        # Bright green
        marker.color = ColorRGBA(r=0.0, g=1.0, b=0.2, a=1.0)
        self.pub_goal_marker.publish(marker)

    def clear_goal_marker(self):
        """Clear active goal marker in RViz."""
        marker = Marker()
        marker.header.frame_id = 'map'
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = 'current_goal'
        marker.id = 999
        marker.action = Marker.DELETE
        self.pub_goal_marker.publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = FrontierExplorerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
