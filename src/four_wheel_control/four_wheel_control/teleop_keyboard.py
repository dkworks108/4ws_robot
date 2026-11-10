#!/usr/bin/env python3
"""
Custom Keyboard Teleoperation Node for Four-Wheel Steering Autonomous Robot.

Supports:
- Forward/Reverse and Steering
- Diagonal and Lateral Crab Strafing
- Rotation-In-Place
- Dynamic Steering Mode Selection (Modes A, B, C, D, E)
- Speed scaling
"""

import sys
import select
import termios
import tty
import os
os.environ.setdefault('PYTHONNOUSERSITE', '1')

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String

from four_wheel_control.kinematics import FourWheelKinematics

INSTRUCTIONS = """
=============================================================
 4-Wheel Steering Mobile Robot - Teleoperation Interface
=============================================================
Movement Controls:
        w
   a    s    d      w/s: Forward / Reverse
                    a/d: Steer Left / Right (yaw rotation)

Crab & Strafing:
   q         e      q/e: Diagonal Forward-Left / Forward-Right
   z         c      z/c: Pure Lateral Strafe Left / Right (90 deg)

In-Place Spin:
   j         l      j/l: Spin CCW / CW in place

Stop:
   SPACE or k       Stop all motion immediately

Speed Adjustments:
   u / m : Increase / Decrease linear speed (+/- 0.05 m/s)
   i / , : Increase / Decrease angular speed (+/- 0.1 rad/s)

Steering Modes:
   1: Mode A - Front-Wheel Steering (rear straight, Ackermann)
   2: Mode B - 4WS Counter-Phase (tight turning)
   3: Mode C - Crab Steering (parallel translation)
   4: Mode D - Generalized Swerve (universal planar)
   5: Mode E - Rotation-In-Place

Press Ctrl-C to quit.
=============================================================
"""


class TeleopKeyboardNode(Node):
    def __init__(self):
        super().__init__('teleop_keyboard')
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_mode = self.create_publisher(String, '/four_wheel/set_mode', 10)

        self.lin_speed = 0.35   # m/s
        self.ang_speed = 0.60   # rad/s
        self.current_mode = FourWheelKinematics.MODE_B_FOUR_WHEEL

        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info("Teleoperation keyboard node initialized.")

    def get_key(self, timeout=0.1):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        key = sys.stdin.read(1) if rlist else ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def run(self):
        print(INSTRUCTIONS)
        vx, vy, wz = 0.0, 0.0, 0.0

        try:
            while rclpy.ok():
                key = self.get_key(timeout=0.05)
                if not key:
                    continue

                if key == '\x03':  # Ctrl-C
                    break

                # Drive commands
                if key == 'w':
                    vx, vy, wz = self.lin_speed, 0.0, 0.0
                elif key == 's':
                    vx, vy, wz = -self.lin_speed, 0.0, 0.0
                elif key == 'a':
                    vx, vy, wz = self.lin_speed * 0.7, 0.0, self.ang_speed
                elif key == 'd':
                    vx, vy, wz = self.lin_speed * 0.7, 0.0, -self.ang_speed
                # Crab commands
                elif key == 'q':
                    vx, vy, wz = self.lin_speed * 0.7, self.lin_speed * 0.7, 0.0
                elif key == 'e':
                    vx, vy, wz = self.lin_speed * 0.7, -self.lin_speed * 0.7, 0.0
                elif key == 'z':
                    vx, vy, wz = 0.0, self.lin_speed, 0.0
                elif key == 'c':
                    vx, vy, wz = 0.0, -self.lin_speed, 0.0
                # In-place spin
                elif key == 'j':
                    vx, vy, wz = 0.0, 0.0, self.ang_speed
                elif key == 'l':
                    vx, vy, wz = 0.0, 0.0, -self.ang_speed
                # Stop
                elif key in (' ', 'k'):
                    vx, vy, wz = 0.0, 0.0, 0.0
                # Speeds
                elif key == 'u':
                    self.lin_speed = min(1.5, self.lin_speed + 0.05)
                    print(f"Linear speed: {self.lin_speed:.2f} m/s")
                elif key == 'm':
                    self.lin_speed = max(0.05, self.lin_speed - 0.05)
                    print(f"Linear speed: {self.lin_speed:.2f} m/s")
                elif key == 'i':
                    self.ang_speed = min(2.5, self.ang_speed + 0.1)
                    print(f"Angular speed: {self.ang_speed:.2f} rad/s")
                elif key == ',':
                    self.ang_speed = max(0.1, self.ang_speed - 0.1)
                    print(f"Angular speed: {self.ang_speed:.2f} rad/s")
                # Mode selection
                elif key == '1':
                    self.current_mode = FourWheelKinematics.MODE_A_FRONT_STEER
                    self.pub_mode.publish(String(data=self.current_mode))
                    print(f"Switched to Mode A (Front-Wheel Steer)")
                elif key == '2':
                    self.current_mode = FourWheelKinematics.MODE_B_FOUR_WHEEL
                    self.pub_mode.publish(String(data=self.current_mode))
                    print(f"Switched to Mode B (4WS Counter-Phase)")
                elif key == '3':
                    self.current_mode = FourWheelKinematics.MODE_C_CRAB
                    self.pub_mode.publish(String(data=self.current_mode))
                    print(f"Switched to Mode C (Crab Steer)")
                elif key == '4':
                    self.current_mode = FourWheelKinematics.MODE_D_GENERALIZED
                    self.pub_mode.publish(String(data=self.current_mode))
                    print(f"Switched to Mode D (Generalized Swerve)")
                elif key == '5':
                    self.current_mode = FourWheelKinematics.MODE_E_IN_PLACE
                    self.pub_mode.publish(String(data=self.current_mode))
                    print(f"Switched to Mode E (Rotation-In-Place)")

                # Publish Twist
                msg = Twist()
                msg.linear.x = float(vx)
                msg.linear.y = float(vy)
                msg.angular.z = float(wz)
                self.pub_cmd_vel.publish(msg)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
            # Send final stop command
            stop_msg = Twist()
            self.pub_cmd_vel.publish(stop_msg)


def main(args=None):
    rclpy.init(args=args)
    teleop = TeleopKeyboardNode()
    try:
        teleop.run()
    except Exception as e:
        print(f"Teleop error: {e}")
    finally:
        teleop.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
