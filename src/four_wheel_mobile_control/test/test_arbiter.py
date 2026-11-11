#!/usr/bin/env python3
"""
Unit and Integration Tests for Command Arbiter & Safety Multiplexer.
"""

import time
import unittest
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Bool, Float32
from std_srvs.srv import Trigger

from four_wheel_mobile_control.command_arbiter_node import CommandArbiterNode


class TestCommandArbiter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        self.arbiter = CommandArbiterNode()
        self.test_node = rclpy.create_node('test_arbiter_client')

        self.last_cmd_vel = None
        self.test_node.create_subscription(
            Twist, '/cmd_vel', self.cb_cmd_vel, 10
        )

    def tearDown(self):
        self.test_node.destroy_node()
        self.arbiter.destroy_node()

    def cb_cmd_vel(self, msg: Twist):
        self.last_cmd_vel = msg

    def spin_short(self, duration=0.1):
        start = time.time()
        while time.time() - start < duration and rclpy.ok():
            rclpy.spin_once(self.arbiter, timeout_sec=0.01)
            rclpy.spin_once(self.test_node, timeout_sec=0.01)

    def test_01_initial_state(self):
        """Verify arbiter initializes in MANUAL mode without E-stop."""
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_MANUAL)
        self.assertFalse(self.arbiter.estop_active)
        self.assertEqual(self.arbiter.speed_limit, 1.0)

    def test_02_mode_transitions(self):
        """Verify switching between modes."""
        self.arbiter.switch_mode(CommandArbiterNode.MODE_NAV)
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_NAV)

        self.arbiter.switch_mode(CommandArbiterNode.MODE_EXPLORE)
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_EXPLORE)

        self.arbiter.switch_mode(CommandArbiterNode.MODE_MANUAL)
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_MANUAL)

    def test_03_estop_override(self):
        """Verify E-stop forces ESTOP mode, latches, and blocks other mode switches."""
        self.arbiter.trigger_estop("Test E-stop")
        self.assertTrue(self.arbiter.estop_active)
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_ESTOP)

        # Attempt to switch to NAV while E-stop is active -> must remain in ESTOP
        self.arbiter.switch_mode(CommandArbiterNode.MODE_NAV)
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_ESTOP)

        # Clear E-stop -> must return to MANUAL
        self.arbiter.reset_estop("Test Clear")
        self.assertFalse(self.arbiter.estop_active)
        self.assertEqual(self.arbiter.current_mode, CommandArbiterNode.MODE_MANUAL)

    def test_04_speed_limit_scaling(self):
        """Verify manual commands are scaled by active speed limit."""
        # 50% limit
        self.arbiter.speed_limit = 0.50

        # Send manual command
        t = Twist()
        t.linear.x = 1.0
        t.linear.y = 0.6
        t.angular.z = 1.2
        self.arbiter.cb_manual_cmd(t)

        # Allow mode transition window to pass
        self.arbiter.mode_transition_time = 0.0

        # Run control cycle
        self.arbiter.control_cycle()
        self.spin_short(0.05)

        self.assertIsNotNone(self.last_cmd_vel)
        self.assertAlmostEqual(self.last_cmd_vel.linear.x, 0.50, places=2)
        self.assertAlmostEqual(self.last_cmd_vel.linear.y, 0.30, places=2)
        self.assertAlmostEqual(self.last_cmd_vel.angular.z, 0.60, places=2)

    def test_05_watchdog_timeout(self):
        """Verify that stale manual commands produce zero velocity."""
        self.arbiter.speed_limit = 1.0
        self.arbiter.mode_transition_time = 0.0

        t = Twist()
        t.linear.x = 0.8
        self.arbiter.cb_manual_cmd(t)

        # Simulate watchdog expiry by setting last_manual_cmd_time far in past
        self.arbiter.last_manual_cmd_time = 0.0
        self.arbiter.control_cycle()
        self.spin_short(0.05)

        self.assertIsNotNone(self.last_cmd_vel)
        self.assertEqual(self.last_cmd_vel.linear.x, 0.0)
        self.assertEqual(self.last_cmd_vel.linear.y, 0.0)
        self.assertEqual(self.last_cmd_vel.angular.z, 0.0)
        self.assertTrue(self.arbiter.watchdog_tripped)


if __name__ == '__main__':
    unittest.main()

