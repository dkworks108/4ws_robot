#!/usr/bin/env python3
"""
Unit tests for 4WS/4WD kinematics engine.

Validates:
- Mode A: Front-Wheel Steer Ackermann geometry
- Mode B: Four-Wheel Steer counter-phase geometry
- Mode C: Crab steering parallel angles and velocity
- Mode D: Generalized planar swerve kinematics
- Mode E: Rotation-In-Place zero translation, maximal yaw torque
- Forward kinematics least-squares planar odometry reconstruction for all modes
- Clamping of steering angles and wheel speeds
"""

import os
import sys
import math
import pytest

WS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WS_ROOT, 'src', 'four_wheel_control'))

from four_wheel_control.kinematics import FourWheelKinematics


@pytest.fixture
def kin():
    return FourWheelKinematics(
        wheelbase=0.36,
        track_width=0.36,
        wheel_radius=0.08,
        max_steering_angle=1.5707963,
        max_wheel_speed=25.0
    )


def test_straight_forward(kin):
    steer, speeds = kin.inverse_kinematics(vx=0.5, vy=0.0, wz=0.0)
    for s in steer:
        assert abs(s) < 1e-4, f"Steering should be zero, got {s}"
    expected_speed = 0.5 / 0.08
    for sp in speeds:
        assert abs(sp - expected_speed) < 1e-3, f"Speed mismatch: {sp} vs {expected_speed}"

    # Forward kinematics verification
    vx, vy, wz = kin.forward_kinematics(steer, speeds)
    assert abs(vx - 0.5) < 1e-3
    assert abs(vy) < 1e-4
    assert abs(wz) < 1e-4


def test_straight_reverse(kin):
    steer, speeds = kin.inverse_kinematics(vx=-0.4, vy=0.0, wz=0.0)
    for s in steer:
        assert abs(s) < 1e-4
    expected_speed = -0.4 / 0.08
    for sp in speeds:
        assert abs(sp - expected_speed) < 1e-3

    vx, vy, wz = kin.forward_kinematics(steer, speeds)
    assert abs(vx - (-0.4)) < 1e-3
    assert abs(vy) < 1e-4
    assert abs(wz) < 1e-4


def test_mode_a_front_steering_ackermann(kin):
    # Left turn: vx = 0.5, wz = 0.5 -> R = 1.0 m
    steer, speeds = kin.inverse_kinematics(
        vx=0.5, vy=0.0, wz=0.5, mode=FourWheelKinematics.MODE_A_FRONT_STEER
    )

    # Rear wheels must be zero
    assert abs(steer[2]) < 1e-4, f"RL steering should be 0, got {steer[2]}"
    assert abs(steer[3]) < 1e-4, f"RR steering should be 0, got {steer[3]}"

    # Front inner wheel (FL) turns sharper than outer (FR) for left turn
    assert steer[0] > steer[1], f"Inner wheel {steer[0]} should turn sharper than outer {steer[1]}"
    assert steer[0] > 0
    assert steer[1] > 0

    # Forward kinematics reconstruction
    vx, vy, wz = kin.forward_kinematics(steer, speeds)
    assert abs(vx - 0.5) < 0.05
    assert abs(wz - 0.5) < 0.05


def test_mode_b_counter_phase_4ws(kin):
    # Left turn in counter-phase
    steer, speeds = kin.inverse_kinematics(
        vx=0.4, vy=0.0, wz=0.8, mode=FourWheelKinematics.MODE_B_FOUR_WHEEL
    )

    # Front wheels positive, rear wheels negative (opposite)
    assert steer[0] > 0, "FL should be positive"
    assert steer[1] > 0, "FR should be positive"
    assert steer[2] < 0, "RL should be negative"
    assert steer[3] < 0, "RR should be negative"

    # Symmetric magnitude
    assert abs(steer[0] + steer[2]) < 1e-4, "FL and RL should be equal and opposite"
    assert abs(steer[1] + steer[3]) < 1e-4, "FR and RR should be equal and opposite"

    # Forward kinematics reconstruction
    vx, vy, wz = kin.forward_kinematics(steer, speeds)
    assert abs(vx - 0.4) < 0.05
    assert abs(wz - 0.8) < 0.05


def test_mode_c_crab_steering(kin):
    # Pure diagonal crab at 45 degrees: vx = 0.3, vy = 0.3, wz = 0
    steer, speeds = kin.inverse_kinematics(
        vx=0.3, vy=0.3, wz=0.0, mode=FourWheelKinematics.MODE_C_CRAB
    )

    expected_angle = math.atan2(0.3, 0.3)  # pi/4 ~ 0.7854
    expected_speed = math.hypot(0.3, 0.3) / 0.08

    for s in steer:
        assert abs(s - expected_angle) < 1e-3, f"Steering mismatch: {s} vs {expected_angle}"
    for sp in speeds:
        assert abs(sp - expected_speed) < 1e-3, f"Speed mismatch: {sp} vs {expected_speed}"

    # Forward kinematics
    vx, vy, wz = kin.forward_kinematics(steer, speeds)
    assert abs(vx - 0.3) < 1e-3
    assert abs(vy - 0.3) < 1e-3
    assert abs(wz) < 1e-4


def test_mode_e_rotation_in_place(kin):
    # Pure rotation CCW: vx = 0, vy = 0, wz = 1.0
    steer, speeds = kin.inverse_kinematics(
        vx=0.0, vy=0.0, wz=1.0, mode=FourWheelKinematics.MODE_E_IN_PLACE
    )

    # Tangential angles for symmetric chassis (+/- 45 deg)
    beta = math.atan2(0.18, 0.18)
    assert abs(abs(steer[0]) - beta) < 1e-3
    assert abs(abs(steer[1]) - beta) < 1e-3
    assert abs(abs(steer[2]) - beta) < 1e-3
    assert abs(abs(steer[3]) - beta) < 1e-3

    # Forward kinematics
    vx, vy, wz = kin.forward_kinematics(steer, speeds)
    assert abs(vx) < 1e-3, f"Translation vx should be 0, got {vx}"
    assert abs(vy) < 1e-3, f"Translation vy should be 0, got {vy}"
    assert abs(wz - 1.0) < 0.05, f"Yaw rate wz mismatch: {wz} vs 1.0"


def test_steering_and_speed_limits(kin):
    # Test extreme command
    steer, speeds = kin.inverse_kinematics(vx=100.0, vy=50.0, wz=50.0)
    for s in steer:
        assert abs(s) <= kin.max_steer + 1e-6
    for sp in speeds:
        assert abs(sp) <= kin.max_wheel_speed + 1e-6


if __name__ == '__main__':
    pytest.main(['-v', __file__])
