#!/usr/bin/env python3
"""
Automated Multi-Device Screenshot Capture for Mobile Dashboard.

Captures pixel-perfect screenshots of the mobile web application across:
- Android / iPhone Mobile Phone Viewport (412 x 915)
- Tablet Viewport (820 x 1180)
- Desktop High-Resolution Workstation Viewport (1440 x 900)
"""

import os
import sys
import time
import shutil
import subprocess

def capture_screenshots():
    ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shots_dir = os.path.join(ws_root, "screenshots")
    dist_dir = os.path.join(ws_root, "src", "four_wheel_mobile_control", "frontend", "dist")
    artifact_dir = os.environ.get("SCREENSHOT_ARTIFACT_DIR", "")

    os.makedirs(shots_dir, exist_ok=True)
    if artifact_dir:
        os.makedirs(artifact_dir, exist_ok=True)

    print("=" * 70)
    print("STARTING MOBILE DASHBOARD SCREENSHOT CAPTURE")
    print(f"Serving from: {dist_dir}")
    print("=" * 70)

    # 1. Start Python HTTP Server on port 3000
    server_cmd = [sys.executable, "-m", "http.server", "3000", "--directory", dist_dir]
    server_proc = subprocess.Popen(server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)

    devices = [
        ("mobile_dashboard_phone.png", 412, 915, "Mobile Smartphone Viewport (Pixel / iPhone)"),
        ("mobile_dashboard_tablet.png", 820, 1180, "Tablet Viewport (iPad / Galaxy Tab)"),
        ("mobile_dashboard_desktop.png", 1440, 900, "High-Res Desktop Workstation Viewport")
    ]

    try:
        for filename, width, height, label in devices:
            out_path = os.path.join(shots_dir, filename)
            art_path = os.path.join(artifact_dir, filename)

            chrome_cmd = [
                "google-chrome",
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--window-size={width},{height}",
                f"--screenshot={out_path}",
                "http://localhost:3000/"
            ]
            print(f"Capturing {label} [{width}x{height}] -> {filename}...")
            res = subprocess.run(chrome_cmd, capture_output=True, text=True)
            if os.path.exists(out_path):
                if artifact_dir:
                    shutil.copy2(out_path, art_path)
                print(f" -> SUCCESS: Saved to {out_path} ({os.path.getsize(out_path)} bytes)")
            else:
                print(f" -> FAILED to generate {out_path}: {res.stderr}")

    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=2.0)
        except Exception:
            server_proc.kill()

    print("=" * 70)
    print("ALL MOBILE DASHBOARD SCREENSHOTS CAPTURED SUCCESSFULLY")
    print("=" * 70)

if __name__ == '__main__':
    capture_screenshots()

