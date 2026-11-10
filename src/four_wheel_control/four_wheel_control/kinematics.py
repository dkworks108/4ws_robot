#!/usr/bin/env python3
"""
Four-Wheel Steering (4WS) and Four-Wheel Drive (4WD) Kinematics Engine.

Supports 5 distinct steering and locomotion modes:
- Mode A: Front-Wheel Steering (rear wheels straight, Ackermann inner/outer angles)
- Mode B: Four-Wheel Steering (counter-phase, symmetric front/rear opposite steering)
- Mode C: Crab Steering (all 4 wheels steer parallel for diagonal translation)
- Mode D: Generalized Swerve / ICR Planar Kinematics (universal planar omnidirectional)
- Mode E: Rotation-In-Place (wheels aligned tangentially to center of rotation)

Also provides closed-form least-squares forward kinematics for odometry computation.
"""

import math
from typing import Tuple, List, Optional
import numpy as np


class FourWheelKinematics:
    """
    Mathematical kinematics model for 4WS/4WD mobile robot.
    Wheel indices:
      0: Front-Left  (FL) at (+a, +b)
      1: Front-Right (FR) at (+a, -b)
      2: Rear-Left   (RL) at (-a, +b)
      3: Rear-Right  (RR) at (-a, -b)
    """

    MODE_A_FRONT_STEER = "front_steer"
    MODE_B_FOUR_WHEEL = "four_wheel_steer"
    MODE_C_CRAB = "crab"
    MODE_D_GENERALIZED = "generalized"
    MODE_E_IN_PLACE = "in_place_spin"

    VALID_MODES = [
        MODE_A_FRONT_STEER,
        MODE_B_FOUR_WHEEL,
        MODE_C_CRAB,
        MODE_D_GENERALIZED,
        MODE_E_IN_PLACE
    ]

    def __init__(
        self,
        wheelbase: float = 0.36,
        track_width: float = 0.36,
        wheel_radius: float = 0.08,
        max_steering_angle: float = 1.5707963,  # +/- 90 deg
        max_wheel_speed: float = 20.0          # rad/s
    ):
        self.L = wheelbase
        self.W = track_width
        self.r = wheel_radius
        self.a = wheelbase / 2.0   # 0.18 m
        self.b = track_width / 2.0  # 0.18 m
        self.max_steer = max_steering_angle
        self.max_wheel_speed = max_wheel_speed

        # Corner positions relative to base_link: (x, y)
        self.wheel_positions = [
            ( self.a,  self.b),  # FL
            ( self.a, -self.b),  # FR
            (-self.a,  self.b),  # RL
            (-self.a, -self.b)   # RR
        ]

        # In-place diagonal distance and angle
        self.R_diag = math.hypot(self.a, self.b)
        self.beta = math.atan2(self.b, self.a)  # ~45 deg (0.7854 rad)

        # Last commanded steering angles for smooth continuity when stopped
        self.last_steering_angles = [0.0, 0.0, 0.0, 0.0]

    def clamp_steer(self, angle: float) -> float:
        """Clamp steering angle to allowed mechanical limits."""
        return max(-self.max_steer, min(self.max_steer, angle))

    def clamp_wheel_speed(self, speed: float) -> float:
        """Clamp wheel angular velocity to max motor speed."""
        return max(-self.max_wheel_speed, min(self.max_wheel_speed, speed))

    def inverse_kinematics(
        self,
        vx: float,
        vy: float,
        wz: float,
        mode: Optional[str] = None
    ) -> Tuple[List[float], List[float]]:
        """
        Compute inverse kinematics for commanded chassis twist (vx, vy, wz).
        Returns:
            (steering_angles [fl, fr, rl, rr], wheel_speeds [fl, fr, rl, rr])
        """
        # Auto-detect mode if not explicitly overridden:
        # If pure rotation commanded (vx=0, vy=0, wz!=0), use Mode E (in-place spin)
        # If lateral velocity commanded without yaw (vy!=0, wz=0), use Mode C (crab)
        # Otherwise use specified mode or default to generalized/4WS
        selected_mode = mode or FourWheelKinematics.MODE_B_FOUR_WHEEL

        # If zero command, hold current steering angles and set zero velocity
        if abs(vx) < 1e-4 and abs(vy) < 1e-4 and abs(wz) < 1e-4:
            return list(self.last_steering_angles), [0.0, 0.0, 0.0, 0.0]

        # Auto-switch to in-place spin if translational speed is zero and wz is significant
        if math.hypot(vx, vy) < 1e-3 and abs(wz) > 1e-3:
            selected_mode = FourWheelKinematics.MODE_E_IN_PLACE

        # Dispatch by mode
        if selected_mode == FourWheelKinematics.MODE_A_FRONT_STEER:
            steer, speed = self._ik_mode_a(vx, wz)
        elif selected_mode == FourWheelKinematics.MODE_B_FOUR_WHEEL:
            steer, speed = self._ik_mode_b(vx, wz)
        elif selected_mode == FourWheelKinematics.MODE_C_CRAB:
            steer, speed = self._ik_mode_c(vx, vy)
        elif selected_mode == FourWheelKinematics.MODE_E_IN_PLACE:
            steer, speed = self._ik_mode_e(wz)
        else:  # MODE_D_GENERALIZED (default fallback)
            steer, speed = self._ik_mode_d(vx, vy, wz)

        # Update last steering angles and return
        self.last_steering_angles = list(steer)
        return steer, speed

    def _ik_mode_a(self, vx: float, wz: float) -> Tuple[List[float], List[float]]:
        """Mode A: Front-wheel steering (rear wheels straight, Ackermann geometry)."""
        if abs(wz) < 1e-4 or abs(vx) < 1e-4:
            # Straight forward/reverse
            wheel_vel = self.clamp_wheel_speed(vx / self.r)
            return [0.0, 0.0, 0.0, 0.0], [wheel_vel] * 4

        # Instantaneous turn radius
        R = vx / wz
        # Rear axle stays at 0 rad
        delta_rl = 0.0
        delta_rr = 0.0
        v_rl = wz * (R - self.b)
        v_rr = wz * (R + self.b)

        # Front axle Ackermann
        # Wheelbase L = 2*a
        delta_fl = math.atan(self.L / (R - self.b))
        delta_fr = math.atan(self.L / (R + self.b))
        v_fl = wz * math.hypot(self.L, R - self.b) * (1.0 if vx >= 0 else -1.0)
        v_fr = wz * math.hypot(self.L, R + self.b) * (1.0 if vx >= 0 else -1.0)

        steer = [
            self.clamp_steer(delta_fl),
            self.clamp_steer(delta_fr),
            self.clamp_steer(delta_rl),
            self.clamp_steer(delta_rr)
        ]
        speeds = [
            self.clamp_wheel_speed(v_fl / self.r),
            self.clamp_wheel_speed(v_fr / self.r),
            self.clamp_wheel_speed(v_rl / self.r),
            self.clamp_wheel_speed(v_rr / self.r)
        ]
        return steer, speeds

    def _ik_mode_b(self, vx: float, wz: float) -> Tuple[List[float], List[float]]:
        """Mode B: 4WS Counter-phase (front and rear steer opposite directions, tight turning)."""
        if abs(wz) < 1e-4 or abs(vx) < 1e-4:
            wheel_vel = self.clamp_wheel_speed(vx / self.r)
            return [0.0, 0.0, 0.0, 0.0], [wheel_vel] * 4

        # Turn radius R
        R = vx / wz
        sign_dir = 1.0 if vx >= 0 else -1.0

        # Front axle steers inward, rear axle steers opposite
        delta_fl = math.atan(self.a / (R - self.b))
        delta_fr = math.atan(self.a / (R + self.b))
        delta_rl = -delta_fl
        delta_rr = -delta_fr

        v_fl = abs(wz) * math.hypot(self.a, R - self.b) * sign_dir
        v_fr = abs(wz) * math.hypot(self.a, R + self.b) * sign_dir
        v_rl = v_fl
        v_rr = v_fr

        steer = [
            self.clamp_steer(delta_fl),
            self.clamp_steer(delta_fr),
            self.clamp_steer(delta_rl),
            self.clamp_steer(delta_rr)
        ]
        speeds = [
            self.clamp_wheel_speed(v_fl / self.r),
            self.clamp_wheel_speed(v_fr / self.r),
            self.clamp_wheel_speed(v_rl / self.r),
            self.clamp_wheel_speed(v_rr / self.r)
        ]
        return steer, speeds

    def _ik_mode_c(self, vx: float, vy: float) -> Tuple[List[float], List[float]]:
        """Mode C: Crab steering (all 4 wheels steer parallel for diagonal translation)."""
        speed_lin = math.hypot(vx, vy)
        if speed_lin < 1e-4:
            return list(self.last_steering_angles), [0.0, 0.0, 0.0, 0.0]

        steer_angle = math.atan2(vy, vx)
        wheel_vel = self.clamp_wheel_speed(speed_lin / self.r)

        steer = [self.clamp_steer(steer_angle)] * 4
        speeds = [wheel_vel] * 4
        return steer, speeds

    def _ik_mode_d(self, vx: float, vy: float, wz: float) -> Tuple[List[float], List[float]]:
        """Mode D: Generalized Swerve / ICR Planar Kinematics."""
        steer = []
        speeds = []

        for x_i, y_i in self.wheel_positions:
            v_ix = vx - wz * y_i
            v_iy = vy + wz * x_i
            v_mag = math.hypot(v_ix, v_iy)

            if v_mag < 1e-4:
                steer.append(0.0)
                speeds.append(0.0)
            else:
                angle = math.atan2(v_iy, v_ix)
                steer.append(self.clamp_steer(angle))
                speeds.append(self.clamp_wheel_speed(v_mag / self.r))

        return steer, speeds

    def _ik_mode_e(self, wz: float) -> Tuple[List[float], List[float]]:
        """
        Mode E: Rotation-In-Place.
        Wheels orient tangentially to origin circle:
        FL: -beta (-45 deg), FR: +beta (+45 deg), RL: +beta (+45 deg), RR: -beta (-45 deg)
        Wheel speeds match tangential direction of rotation.
        """
        if abs(wz) < 1e-4:
            return list(self.last_steering_angles), [0.0, 0.0, 0.0, 0.0]

        # Orientation tangents (in robot body frame, perpendicular to radial vector)
        # Radial vectors: FL:(+a, +b), FR:(+a, -b), RL:(-a, +b), RR:(-a, -b)
        # Tangents for CCW (+wz):
        # FL: (-b, +a) -> angle = atan2(a, -b) = 135 deg or -45 deg reversed
        # For simplicity and small joint range:
        # Orient wheels to tangent lines:
        steer = [
            -self.beta,  # FL (-0.7854 rad)
             self.beta,  # FR (+0.7854 rad)
             self.beta,  # RL (+0.7854 rad)
            -self.beta   # RR (-0.7854 rad)
        ]

        # Speed magnitudes: v_tan = wz * R_diag
        # With steering angles defined above:
        # Positive wheel spin for FR and RR drives CCW rotation
        # Negative wheel spin for FL and RL drives CCW rotation
        v_tan = wz * self.R_diag
        w_val = v_tan / self.r

        speeds = [
            self.clamp_wheel_speed(-w_val),  # FL
            self.clamp_wheel_speed( w_val),  # FR
            self.clamp_wheel_speed(-w_val),  # RL
            self.clamp_wheel_speed( w_val)   # RR
        ]
        return steer, speeds

    def forward_kinematics(
        self,
        steering_angles: List[float],
        wheel_speeds: List[float]
    ) -> Tuple[float, float, float]:
        """
        Compute robot planar chassis velocity (vx, vy, wz) from measured wheel states.
        Uses exact analytical least-squares pseudo-inverse over 4 wheel velocity vectors.
        """
        if len(steering_angles) != 4 or len(wheel_speeds) != 4:
            return 0.0, 0.0, 0.0

        v_ix_list = []
        v_iy_list = []

        for i in range(4):
            v_lin = wheel_speeds[i] * self.r
            delta = steering_angles[i]
            v_ix_list.append(v_lin * math.cos(delta))
            v_iy_list.append(v_lin * math.sin(delta))

        # Closed-form least squares solution for symmetric 4-wheel base:
        # A^T A = diag([4, 4, 4*(a^2 + b^2)])
        vx = sum(v_ix_list) / 4.0
        vy = sum(v_iy_list) / 4.0

        denom = 4.0 * (self.a**2 + self.b**2)
        torque_sum = 0.0
        for i, (x_i, y_i) in enumerate(self.wheel_positions):
            torque_sum += (-y_i * v_ix_list[i] + x_i * v_iy_list[i])

        wz = torque_sum / denom if denom > 1e-6 else 0.0
        return vx, vy, wz
