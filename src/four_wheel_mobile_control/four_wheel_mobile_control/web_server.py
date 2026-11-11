#!/usr/bin/env python3
"""
Lightweight Static HTTP Server for Four-Wheel Mobile Control Dashboard.

Serves the built React/Vite dashboard bundle across the local area network (LAN),
exposing the web interface to mobile devices (Android, iOS), tablets, and PCs.
"""

import os
import sys
import json
import socket
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def get_local_ip_addresses():
    """Discover all non-loopback IPv4 addresses on the host system."""
    ip_list = []
    try:
        # Connect to a public DNS IP (doesn't send packets) to find default routing interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and not primary_ip.startswith('127.'):
            ip_list.append(primary_ip)
    except Exception:
        pass

    try:
        import netifaces
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr_info in addrs[netifaces.AF_INET]:
                    ip = addr_info.get('addr')
                    if ip and not ip.startswith('127.') and ip not in ip_list:
                        ip_list.append(ip)
    except Exception:
        # Fallback using `ip -4 -o addr show` on Linux when netifaces is unavailable
        try:
            out = subprocess.check_output(
                ['ip', '-4', '-o', 'addr', 'show'],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1.5,
            )
            for line in out.splitlines():
                parts = line.split()
                for idx, tok in enumerate(parts):
                    if tok == 'inet' and idx + 1 < len(parts):
                        ip = parts[idx + 1].split('/')[0]
                        if ip and not ip.startswith('127.') and ip not in ip_list:
                            ip_list.append(ip)
        except Exception:
            pass

    if not ip_list:
        ip_list.append("127.0.0.1")
    return ip_list


class DashboardHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler supporting SPA routing and config API."""

    frontend_dir = ""
    config_data = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.frontend_dir, **kwargs)

    def do_GET(self):
        # API health endpoint
        if self.path == '/api/health' or self.path == '/api/health/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            health_payload = {
                'status': 'ok',
                'primary_ip': self.config_data.get('primary_ip', '127.0.0.1'),
                'rosbridge_port': self.config_data.get('rosbridge_port', 9090),
                'web_video_port': self.config_data.get('web_video_port', 8080),
            }
            self.wfile.write(json.dumps(health_payload).encode('utf-8'))
            return

        # API config endpoint
        if self.path == '/api/config' or self.path == '/api/config/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(self.config_data).encode('utf-8'))
            return

        # SPA fallback: if requested file doesn't exist, serve index.html
        path_without_query = self.path.split('?')[0]
        local_path = os.path.join(self.frontend_dir, path_without_query.lstrip('/'))
        if not os.path.exists(local_path) or os.path.isdir(local_path):
            index_path = os.path.join(self.frontend_dir, 'index.html')
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        return super().do_GET()

    def log_message(self, format, *args):
        # Suppress verbose HTTP access logs to keep ROS console clean
        pass


class MobileDashboardWebServer(Node):
    """ROS 2 Node managing the HTTP Web Server for mobile dashboard clients."""

    def __init__(self):
        super().__init__('mobile_dashboard_web_server')

        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('port', 3000)
        self.declare_parameter('rosbridge_port', 9090)
        self.declare_parameter('web_video_port', 8080)
        self.declare_parameter('static_dir', '')

        host = self.get_parameter('host').value
        port = self.get_parameter('port').value
        rosbridge_port = self.get_parameter('rosbridge_port').value
        web_video_port = self.get_parameter('web_video_port').value
        static_dir = self.get_parameter('static_dir').value

        # Locate frontend static files dynamically (package share -> relative source tree)
        if not static_dir:
            candidates = []
            try:
                pkg_share = get_package_share_directory('four_wheel_mobile_control')
                candidates.append(os.path.join(pkg_share, 'frontend'))
            except Exception:
                pass
            pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates.append(os.path.join(pkg_root, 'frontend', 'dist'))
            for c in candidates:
                if os.path.exists(os.path.join(c, 'index.html')):
                    static_dir = c
                    break
            if not static_dir:
                static_dir = candidates[0] if candidates else pkg_root

        # Ensure directory exists or fallback to parent frontend dir
        if not os.path.exists(static_dir):
            parent_dir = os.path.dirname(static_dir)
            if os.path.exists(parent_dir):
                static_dir = parent_dir
            else:
                os.makedirs(static_dir, exist_ok=True)

        local_ips = get_local_ip_addresses()
        primary_ip = local_ips[0]

        config_data = {
            'rosbridge_port': rosbridge_port,
            'web_video_port': web_video_port,
            'detected_ips': local_ips,
            'primary_ip': primary_ip,
            'camera_topic': '/camera/image_raw',
            'lidar_topic': '/scan',
            'odom_topic': '/odom',
            'map_topic': '/map',
            'plan_topic': '/plan'
        }

        DashboardHTTPRequestHandler.frontend_dir = static_dir
        DashboardHTTPRequestHandler.config_data = config_data

        # Start HTTP server on separate daemon thread
        self.httpd = ReusableHTTPServer((host, port), DashboardHTTPRequestHandler)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

        # Log connection banner
        self.get_logger().info("=" * 65)
        self.get_logger().info("🚀 FOUR-WHEEL MOBILE CONTROL DASHBOARD ACTIVE")
        self.get_logger().info(f"   Local Access:     http://localhost:{port}")
        for ip in local_ips:
            self.get_logger().info(f"   Mobile Device:    http://{ip}:{port}")
        self.get_logger().info(f"   WebSocket Bridge: ws://{primary_ip}:{rosbridge_port}")
        self.get_logger().info(f"   Web Video Server: http://{primary_ip}:{web_video_port}")
        self.get_logger().info(f"   Serving Content:  {static_dir}")
        self.get_logger().info("=" * 65)

    def destroy_node(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MobileDashboardWebServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

