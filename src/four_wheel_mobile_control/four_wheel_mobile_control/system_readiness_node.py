#!/usr/bin/env python3
"""
System Readiness and Runtime Health Monitoring Node for Project 04.

Separates startup readiness verification from continuous runtime health monitoring.
Reports overall system state (STARTING, READY, DEGRADED, FAILED, STOPPING) and
actively verifies real evidence for every required subsystem:
- Gazebo (/clock advancing)
- Robot (8 actuated joints present in /joint_states)
- Controllers (/controller_manager/list_controllers: 9 controllers 'active')
- Kinematics (/four_wheel/current_mode publishing)
- Odometry (/odom valid messages)
- LiDAR (/scan valid messages)
- IMU (/imu/data valid messages)
- Camera (/camera/image_raw actual image frames)
- TF (odom->base_footprint->sensors, plus map->odom when SLAM active)
- SLAM (/map OccupancyGrid publishing)
- Nav2 (lifecycle nodes ACTIVE + navigate_to_pose action server ready)
- Exploration (/exploration/start service + /exploration/status)
- Command Arbiter (/mobile/arbiter_status JSON)
- Web Backend (HTTP /api/health 200 OK)
- ROS Bridge (WebSocket HTTP 101 Switching Protocols handshake)
- Video Server (HTTP response on video port)
"""

import os
import sys
import json
import time
import math
import base64
import socket
import urllib.request
import urllib.error
from typing import Dict, Any, List

os.environ.setdefault('PYTHONNOUSERSITE', '1')

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy

from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState, LaserScan, Imu, Image
from nav_msgs.msg import OccupancyGrid, Odometry
from std_msgs.msg import String, Bool
from nav2_msgs.action import NavigateToPose
from std_srvs.srv import Trigger
from controller_manager_msgs.srv import ListControllers
from lifecycle_msgs.srv import GetState

import tf2_ros
from tf2_ros import Buffer, TransformListener


def get_primary_lan_ip() -> str:
    """Discover the primary outward-facing LAN IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


class SystemReadinessNode(Node):
    """Monitors live ROS topics, controllers, lifecycles, TF, services, and network endpoints."""

    STATE_STARTING = "STARTING"
    STATE_READY = "READY"
    STATE_DEGRADED = "DEGRADED"
    STATE_FAILED = "FAILED"
    STATE_STOPPING = "STOPPING"

    EXPECTED_JOINTS = {
        'fl_steering_joint', 'fr_steering_joint',
        'rl_steering_joint', 'rr_steering_joint',
        'fl_wheel_joint', 'fr_wheel_joint',
        'rl_wheel_joint', 'rr_wheel_joint',
    }

    EXPECTED_CONTROLLERS = {
        'joint_state_broadcaster',
        'fl_steering_controller',
        'fr_steering_controller',
        'rl_steering_controller',
        'rr_steering_controller',
        'fl_wheel_controller',
        'fr_wheel_controller',
        'rl_wheel_controller',
        'rr_wheel_controller',
    }

    NAV2_LIFECYCLE_NODES = [
        'controller_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
    ]

    def __init__(self):
        super().__init__('system_readiness_node')

        def safe_param(name, default):
            if not self.has_parameter(name):
                self.declare_parameter(name, default)
            return self.get_parameter(name).value

        def as_bool(val):
            if isinstance(val, str):
                return val.strip().lower() not in ('false', '0', 'no', '')
            return bool(val)

        req_gazebo = as_bool(safe_param('require_gazebo', True))
        req_robot = as_bool(safe_param('require_robot', True))
        req_controllers = as_bool(safe_param('require_controllers', True))
        req_kinematics = as_bool(safe_param('require_kinematics', True))
        req_odom = as_bool(safe_param('require_odom', True))
        req_lidar = as_bool(safe_param('require_lidar', True))
        req_imu = as_bool(safe_param('require_imu', True))
        req_camera = as_bool(safe_param('require_camera', True))
        req_tf = as_bool(safe_param('require_tf', True))
        req_slam = as_bool(safe_param('require_slam', True))
        req_nav2 = as_bool(safe_param('require_nav2', True))
        req_exploration = as_bool(safe_param('require_exploration', True))
        req_arbiter = as_bool(safe_param('require_arbiter', True))
        req_rosbridge = as_bool(safe_param('require_rosbridge', True))
        req_dashboard = as_bool(safe_param('require_dashboard', True))
        req_video = as_bool(safe_param('require_video_server', True))

        self.web_port = int(safe_param('web_port', 3000))
        self.rosbridge_port = int(safe_param('rosbridge_port', 9090))
        self.video_port = int(safe_param('video_port', 8080))
        self.timeout_sec = float(safe_param('timeout_sec', 90.0))
        safe_param('use_sim_time', True)

        def make_entry(required: bool, label: str, stale_timeout: float = 10.0) -> Dict[str, Any]:
            return {
                'required': required,
                'ready': False,
                'healthy': False,
                'label': label,
                'last_seen': 0.0,
                'stale_timeout': stale_timeout,
                'detail': 'pending',
            }

        self.status: Dict[str, Dict[str, Any]] = {
            'Gazebo': make_entry(req_gazebo, 'RUNNING', stale_timeout=5.0),
            'Robot': make_entry(req_robot, 'SPAWNED', stale_timeout=5.0),
            'Controllers': make_entry(req_controllers, 'ACTIVE', stale_timeout=10.0),
            'Kinematics': make_entry(req_kinematics, 'ACTIVE', stale_timeout=6.0),
            'Odometry': make_entry(req_odom, 'ACTIVE', stale_timeout=5.0),
            'LiDAR': make_entry(req_lidar, 'ACTIVE', stale_timeout=5.0),
            'IMU': make_entry(req_imu, 'ACTIVE', stale_timeout=5.0),
            'Camera': make_entry(req_camera, 'ACTIVE', stale_timeout=6.0),
            'TF': make_entry(req_tf, 'VALID', stale_timeout=6.0),
            'SLAM': make_entry(req_slam, 'ACTIVE', stale_timeout=30.0),
            'Nav2': make_entry(req_nav2, 'ACTIVE', stale_timeout=15.0),
            'Exploration': make_entry(req_exploration, 'READY', stale_timeout=10.0),
            'Command Arbiter': make_entry(req_arbiter, 'ACTIVE', stale_timeout=5.0),
            'ROS Bridge': make_entry(req_rosbridge, 'CONNECTED', stale_timeout=10.0),
            'Mobile Dashboard': make_entry(req_dashboard, 'RUNNING', stale_timeout=10.0),
            'Video Server': make_entry(req_video, 'STREAMING', stale_timeout=10.0),
        }

        self.system_state = self.STATE_STARTING
        self.start_wall_time = time.monotonic()
        self.startup_completed = False
        self.last_clock_val = -1.0
        self.clock_advances = 0

        # TF buffer & listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Latched publishers for system readiness & periodic health
        latched_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.pub_ready = self.create_publisher(Bool, '/system/system_ready', latched_qos)
        self.pub_status_json = self.create_publisher(String, '/system/readiness_status', latched_qos)

        # Topic Subscriptions
        self.sub_clock = self.create_subscription(Clock, '/clock', self._cb_clock, 10)
        self.sub_joints = self.create_subscription(JointState, '/joint_states', self._cb_joints, 10)
        self.sub_mode = self.create_subscription(String, '/four_wheel/current_mode', self._cb_kinematics, 10)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self._cb_odom, 10)
        self.sub_scan = self.create_subscription(LaserScan, '/scan', self._cb_scan, 10)
        self.sub_imu = self.create_subscription(Imu, '/imu/data', self._cb_imu, 10)
        self.sub_camera = self.create_subscription(Image, '/camera/image_raw', self._cb_camera, 10)
        self.sub_map = self.create_subscription(OccupancyGrid, '/map', self._cb_map, 10)
        self.sub_arbiter = self.create_subscription(String, '/mobile/arbiter_status', self._cb_arbiter, 10)
        self.sub_explore_stat = self.create_subscription(String, '/exploration/status', self._cb_explore_status, 10)

        # Service & Action Clients
        self.cli_list_controllers = self.create_client(
            ListControllers, '/controller_manager/list_controllers'
        )
        self.nav_action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.cli_explore_start = self.create_client(Trigger, '/exploration/start')
        self.nav2_state_clients = {
            name: self.create_client(GetState, f'/{name}/get_state')
            for name in self.NAV2_LIFECYCLE_NODES
        }

        self._ctrl_query_in_flight = False
        self._nav2_state_values: Dict[str, int] = {}
        self._nav2_queries_in_flight: Dict[str, bool] = {n: False for n in self.NAV2_LIFECYCLE_NODES}
        self._last_net_check = 0.0

        # Periodic health check timer (1 Hz)
        self.check_timer = self.create_timer(1.0, self._check_system_health)
        self.get_logger().info("SystemReadinessNode initialized. Monitoring Project 04 launch pipeline...")

    def _mark_seen(self, key: str, detail: str = "ok"):
        now = time.monotonic()
        entry = self.status[key]
        entry['ready'] = True
        entry['healthy'] = True
        entry['last_seen'] = now
        entry['detail'] = detail

    def _cb_clock(self, msg: Clock):
        current = msg.clock.sec + msg.clock.nanosec * 1e-9
        if self.last_clock_val >= 0.0 and current > self.last_clock_val:
            self.clock_advances += 1
            if self.clock_advances >= 2:
                self._mark_seen('Gazebo', f'sim_time={current:.2f}s')
        self.last_clock_val = current

    def _cb_joints(self, msg: JointState):
        received_joints = set(msg.name)
        if self.EXPECTED_JOINTS.issubset(received_joints):
            self._mark_seen('Robot', '8/8 joints present')

    def _cb_kinematics(self, msg: String):
        if msg.data.strip():
            self._mark_seen('Kinematics', f'mode={msg.data.strip()}')

    def _cb_odom(self, msg: Odometry):
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        vx = msg.twist.twist.linear.x
        if all(math.isfinite(v) for v in (px, py, vx)):
            self._mark_seen('Odometry', f'frame={msg.header.frame_id}->{msg.child_frame_id}')

    def _cb_scan(self, msg: LaserScan):
        if len(msg.ranges) > 0 and msg.range_max > 0:
            self._mark_seen('LiDAR', f'{len(msg.ranges)} beams ({msg.header.frame_id})')

    def _cb_imu(self, msg: Imu):
        if abs(msg.orientation.w) > 1e-5 or abs(msg.linear_acceleration.z) > 1e-3:
            self._mark_seen('IMU', f'frame={msg.header.frame_id}')

    def _cb_camera(self, msg: Image):
        if msg.width > 0 and msg.height > 0 and len(msg.data) > 0:
            self._mark_seen('Camera', f'{msg.width}x{msg.height} {msg.encoding}')

    def _cb_map(self, msg: OccupancyGrid):
        if msg.info.width > 0 and msg.info.height > 0 and len(msg.data) > 0:
            self._mark_seen('SLAM', f'{msg.info.width}x{msg.info.height}@{msg.info.resolution:.2f}m')

    def _cb_arbiter(self, msg: String):
        try:
            data = json.loads(msg.data)
            mode = data.get('operating_mode', 'UNKNOWN')
            self._mark_seen('Command Arbiter', f'mode={mode}')
        except Exception:
            pass

    def _cb_explore_status(self, msg: String):
        if len(msg.data) > 0 and self.cli_explore_start.service_is_ready():
            self._mark_seen('Exploration', f'state={msg.data.strip()}')

    def _query_controllers(self):
        if not self.status['Controllers']['required']:
            return
        if self._ctrl_query_in_flight:
            return
        if not self.cli_list_controllers.service_is_ready():
            self.status['Controllers']['detail'] = 'controller_manager unavailable'
            return
        self._ctrl_query_in_flight = True
        future = self.cli_list_controllers.call_async(ListControllers.Request())
        future.add_done_callback(self._on_controllers_response)

    def _on_controllers_response(self, future):
        self._ctrl_query_in_flight = False
        try:
            resp = future.result()
            active = {c.name for c in resp.controller if c.state == 'active'}
            missing = self.EXPECTED_CONTROLLERS - active
            if not missing:
                self._mark_seen('Controllers', f'{len(self.EXPECTED_CONTROLLERS)}/{len(self.EXPECTED_CONTROLLERS)} active')
            else:
                self.status['Controllers']['healthy'] = False
                self.status['Controllers']['detail'] = f'inactive/missing: {sorted(missing)}'
        except Exception as e:
            self.status['Controllers']['healthy'] = False
            self.status['Controllers']['detail'] = f'query error: {e}'

    def _query_nav2(self):
        if not self.status['Nav2']['required']:
            return
        action_ready = self.nav_action_client.server_is_ready()
        for name, client in self.nav2_state_clients.items():
            if not self._nav2_queries_in_flight[name] and client.service_is_ready():
                self._nav2_queries_in_flight[name] = True
                fut = client.call_async(GetState.Request())
                fut.add_done_callback(lambda f, n=name: self._on_nav2_state(n, f))

        active_nodes = [n for n, st in self._nav2_state_values.items() if st == 3]
        if action_ready and len(active_nodes) == len(self.NAV2_LIFECYCLE_NODES):
            self._mark_seen('Nav2', 'all 4 lifecycle nodes ACTIVE + action ready')
        else:
            self.status['Nav2']['healthy'] = False
            self.status['Nav2']['detail'] = (
                f'active={len(active_nodes)}/{len(self.NAV2_LIFECYCLE_NODES)}, '
                f'action_ready={action_ready}'
            )

    def _on_nav2_state(self, node_name: str, future):
        self._nav2_queries_in_flight[node_name] = False
        try:
            resp = future.result()
            self._nav2_state_values[node_name] = resp.current_state.id
        except Exception:
            pass

    def _check_tf_tree(self):
        if not self.status['TF']['required']:
            return
        pairs = [
            ('odom', 'base_footprint'),
            ('base_footprint', 'lidar_link'),
            ('base_footprint', 'imu_link'),
        ]
        if self.status['Camera']['required']:
            pairs.append(('base_footprint', 'camera_optical_link'))
        if self.status['SLAM']['required']:
            pairs.append(('map', 'odom'))

        missing: List[str] = []
        for parent, child in pairs:
            try:
                self.tf_buffer.lookup_transform(parent, child, Time(), timeout=Duration(seconds=0.0))
            except Exception:
                missing.append(f'{parent}->{child}')

        if not missing:
            self._mark_seen('TF', f'{len(pairs)}/{len(pairs)} transforms valid')
        else:
            self.status['TF']['healthy'] = False
            self.status['TF']['detail'] = f'missing: {", ".join(missing)}'

    def _check_rosbridge_ws_handshake(self) -> bool:
        """Perform an actual HTTP 101 WebSocket upgrade handshake against rosbridge."""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.8)
            sock.connect(('127.0.0.1', self.rosbridge_port))
            key = base64.b64encode(os.urandom(16)).decode('ascii')
            req = (
                f"GET / HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.rosbridge_port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(req.encode('ascii'))
            resp = sock.recv(512).decode('latin1', errors='ignore')
            return '101' in resp.split('\r\n')[0]
        except Exception:
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _check_network_services(self):
        """Check WebSocket handshake, web backend HTTP health, and video server HTTP."""
        # 1. Rosbridge WebSocket handshake
        if self.status['ROS Bridge']['required']:
            if self._check_rosbridge_ws_handshake():
                self._mark_seen('ROS Bridge', f'ws port {self.rosbridge_port} handshake 101 OK')
            else:
                self.status['ROS Bridge']['healthy'] = False
                self.status['ROS Bridge']['detail'] = f'ws port {self.rosbridge_port} unreachable'

        # 2. Mobile Dashboard HTTP Server
        if self.status['Mobile Dashboard']['required']:
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self.web_port}/api/health",
                    headers={'User-Agent': 'SystemReadinessMonitor'}
                )
                with urllib.request.urlopen(req, timeout=0.6) as resp:
                    if resp.status == 200:
                        self._mark_seen('Mobile Dashboard', f'http port {self.web_port} 200 OK')
            except Exception as e:
                self.status['Mobile Dashboard']['healthy'] = False
                self.status['Mobile Dashboard']['detail'] = f'http error: {e}'

        # 3. Web Video Server
        if self.status['Video Server']['required']:
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self.video_port}/",
                    headers={'User-Agent': 'SystemReadinessMonitor'}
                )
                with urllib.request.urlopen(req, timeout=0.6) as resp:
                    if resp.status in (200, 404):
                        self._mark_seen('Video Server', f'http port {self.video_port} responding')
            except urllib.error.HTTPError as e:
                # web_video_server returns 404 or 200 on root index depending on version
                if e.code in (200, 404):
                    self._mark_seen('Video Server', f'http port {self.video_port} responding ({e.code})')
                else:
                    self.status['Video Server']['healthy'] = False
                    self.status['Video Server']['detail'] = f'http status {e.code}'
            except Exception as e:
                self.status['Video Server']['healthy'] = False
                self.status['Video Server']['detail'] = f'http error: {e}'

    def _check_exploration_service(self):
        if self.status['Exploration']['required']:
            if self.cli_explore_start.service_is_ready() and self.status['Exploration']['last_seen'] > 0.0:
                self._mark_seen('Exploration', 'service + status active')
            elif self.cli_explore_start.service_is_ready():
                self.status['Exploration']['detail'] = 'service ready, waiting for status'

    def _refresh_runtime_staleness(self):
        now = time.monotonic()
        for name, info in self.status.items():
            if not info['required'] or not info['ready']:
                continue
            age = now - info['last_seen']
            if age > info['stale_timeout']:
                info['healthy'] = False
                info['detail'] = f'stale ({age:.1f}s)'

    def _publish_health_json(self):
        payload = {
            'system_state': self.system_state,
            'timestamp_wall': time.time(),
            'timestamp_ros': self.get_clock().now().nanoseconds / 1e9,
            'uptime_sec': round(time.monotonic() - self.start_wall_time, 1),
            'components': {
                name: {
                    'required': info['required'],
                    'ready': info['ready'],
                    'healthy': info['healthy'],
                    'detail': info['detail'],
                }
                for name, info in self.status.items()
            },
        }
        self.pub_status_json.publish(String(data=json.dumps(payload)))

    def _check_system_health(self):
        """Main 1 Hz evaluation function."""
        now = time.monotonic()
        net_interval = 5.0 if self.startup_completed else 2.0
        self._query_controllers()
        self._query_nav2()
        self._check_tf_tree()
        if (now - self._last_net_check) >= net_interval:
            self._last_net_check = now
            self._check_network_services()
        self._check_exploration_service()
        self._refresh_runtime_staleness()

        required_items = [name for name, info in self.status.items() if info['required']]
        ready_items = [name for name in required_items if self.status[name]['ready']]
        unhealthy_items = [name for name in required_items if not self.status[name]['healthy']]
        elapsed = time.monotonic() - self.start_wall_time

        if not self.startup_completed:
            if len(ready_items) == len(required_items):
                self.system_state = self.STATE_READY
                self.startup_completed = True
                self._announce_system_ready()
            else:
                missing = [name for name in required_items if not self.status[name]['ready']]
                if int(elapsed) % 5 == 0 and elapsed > 2.0:
                    self.get_logger().info(
                        f"[{self.STATE_STARTING}] ({len(ready_items)}/{len(required_items)} ready). "
                        f"Awaiting: {', '.join(missing)}"
                    )
                if elapsed > self.timeout_sec:
                    self.system_state = self.STATE_FAILED
                    self.startup_completed = True
                    self.pub_ready.publish(Bool(data=False))
                    self.get_logger().error(
                        f"[{self.STATE_FAILED}] Readiness timeout reached after {self.timeout_sec:.0f}s! "
                        f"Missing subsystems: {', '.join(missing)}"
                    )
                    self._print_banner(partial=True)
        else:
            # Runtime health phase (post-startup)
            prev_state = self.system_state
            if prev_state != self.STATE_FAILED:
                if unhealthy_items:
                    self.system_state = self.STATE_DEGRADED
                    if prev_state != self.STATE_DEGRADED:
                        self.get_logger().warn(
                            f"[{self.STATE_DEGRADED}] Runtime degradation detected: {', '.join(unhealthy_items)}"
                        )
                else:
                    self.system_state = self.STATE_READY
                    if prev_state == self.STATE_DEGRADED:
                        self.get_logger().info(f"[{self.STATE_READY}] All subsystems recovered.")

        self._publish_health_json()

    def _announce_system_ready(self):
        """Print verified readiness banner with only live/listening URLs."""
        self.pub_ready.publish(Bool(data=True))
        lan_ip = get_primary_lan_ip()

        banner_lines = [
            "",
            "PROJECT 04 SYSTEM READY",
            f"State:              {self.system_state}",
            "",
        ]
        for name, info in self.status.items():
            if not info['required']:
                state_str = "DISABLED"
            else:
                state_str = info['label'] if info['ready'] else "OFFLINE"
            banner_lines.append(f"{name + ':':<20}{state_str} ({info['detail']})")

        banner_lines.append("")
        banner_lines.append("PROJECT 04 — NETWORK SERVICES")
        if self.status['Mobile Dashboard']['ready']:
            banner_lines.extend([
                "",
                "Desktop:",
                f"http://localhost:{self.web_port}",
                "",
                "Mobile:",
                f"http://{lan_ip}:{self.web_port}",
            ])
        if self.status['ROS Bridge']['ready']:
            banner_lines.extend([
                "",
                "ROS Bridge:",
                f"ws://{lan_ip}:{self.rosbridge_port}",
            ])
        if self.status['Video Server']['ready']:
            banner_lines.extend([
                "",
                "Camera:",
                f"http://{lan_ip}:{self.video_port}",
            ])
        banner_lines.append("")

        print("\n".join(banner_lines), flush=True)
        self.get_logger().info("All Project 04 subsystems verified operational.")

    def _print_banner(self, partial: bool = False):
        lan_ip = get_primary_lan_ip()
        print(f"\n=== PROJECT 04 SUBSYSTEM STATUS ({self.system_state}) ===", flush=True)
        for name, info in self.status.items():
            if not info['required']:
                state = 'DISABLED'
            else:
                state = info['label'] if info['ready'] else f"FAILED/OFFLINE ({info['detail']})"
            print(f"{name:<20}: {state}", flush=True)
        if self.status['Mobile Dashboard']['ready']:
            print(f"\nMobile URL: http://{lan_ip}:{self.web_port}", flush=True)

    def publish_stopping(self):
        self.system_state = self.STATE_STOPPING
        self._publish_health_json()


def main(args=None):
    rclpy.init(args=args)
    node = SystemReadinessNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_stopping()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
