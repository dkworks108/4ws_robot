# Four-Wheel Steering Autonomous Mobile Robot — Steering Kinematics

## 1. Kinematic Geometry & Notation

Let the robot frame be attached to the robot's center of geometry $\mathcal{O}_{base}$, with the positive $X$-axis pointing forward, positive $Y$-axis pointing to the robot's left, and positive $Z$-axis pointing upwards.

The four wheel pivot coordinates $(x_i, y_i)$ relative to $\mathcal{O}_{base}$ are:

$$\begin{aligned}
\text{Front-Left (FL)}: \quad &(x_1, y_1) = (+L/2, +W/2) \\
\text{Front-Right (FR)}: \quad &(x_2, y_2) = (+L/2, -W/2) \\
\text{Rear-Left (RL)}: \quad &(x_3, y_3) = (-L/2, +W/2) \\
\text{Rear-Right (RR)}: \quad &(x_4, y_4) = (-L/2, -W/2)
\end{aligned}$$

where:
- Wheelbase $L = 0.360$ m
- Track width $W = 0.360$ m
- Wheel radius $r = 0.080$ m

Each wheel $i \in \{1, 2, 3, 4\}$ is governed by two control variables:
1. $\delta_i \in [-\pi/2, \pi/2]$: The steering angle of the knuckle around its local vertical axis.
2. $\omega_i \in \mathbb{R}$: The rotational spin rate of the wheel around its axle, producing linear ground contact speed $v_i = \omega_i \cdot r$.

---

## 2. The Five Locomotion & Steering Modes

### Mode A: Front Ackermann Steering (`front_steer`)
In Mode A, the rear wheels remain aligned with the longitudinal chassis axis ($\delta_3 = \delta_4 = 0$), and only the front wheels steer to trace concentric circles whose Instantaneous Center of Rotation (ICR) lies along the extended line of the rear axle ($x_{ICR} = -L/2$).

For a requested turning radius $R$ measured from the rear axle center to the ICR:
$$\tan(\delta_{front\_center}) = \frac{L}{R}$$

The inner and outer steering angles satisfy true Ackermann geometry:
$$\begin{aligned}
\delta_1 (\text{FL}) &= \operatorname{atan2}\left(L, R - \frac{W}{2}\right) \\
\delta_2 (\text{FR}) &= \operatorname{atan2}\left(L, R + \frac{W}{2}\right) \\
\delta_3 (\text{RL}) &= 0 \\
\delta_4 (\text{RR}) &= 0
\end{aligned}$$

Wheel ground speeds are scaled proportionally to their respective radii from the ICR:
$$v_i = \omega_{base} \cdot \sqrt{(x_i - x_{ICR})^2 + (y_i - y_{ICR})^2}$$

---

### Mode B: Four-Wheel Steering Counter-Phase (`four_wheel_steer`)
To achieve tight turns in narrow corridors without lateral tire scrub, Mode B steers front and rear wheels in opposite directions. The Instantaneous Center of Rotation lies on the robot's lateral midline ($x_{ICR} = 0, y_{ICR} = R$).

For a body yaw rate $\omega_z$ and forward velocity $v_x$, the turning radius is $R = v_x / \omega_z$.

The individual steering angles are:
$$\begin{aligned}
\delta_1 (\text{FL}) &= \operatorname{atan2}\left(+\frac{L}{2}, R - \frac{W}{2}\right) \\
\delta_2 (\text{FR}) &= \operatorname{atan2}\left(+\frac{L}{2}, R + \frac{W}{2}\right) \\
\delta_3 (\text{RL}) &= \operatorname{atan2}\left(-\frac{L}{2}, R - \frac{W}{2}\right) = -\delta_1 \\
\delta_4 (\text{RR}) &= \operatorname{atan2}\left(-\frac{L}{2}, R + \frac{W}{2}\right) = -\delta_2
\end{aligned}$$

**Key Advantage:** The turning radius is halved compared to Mode A, and the vehicle enters corners with balanced lateral grip.

---

### Mode C: Crab Steering (`crab`)
Mode C enables diagonal translation while keeping vehicle heading completely constant ($\omega_z = 0$). All four steering knuckles are turned to the exact same angle $\delta_{crab}$:

$$\delta_1 = \delta_2 = \delta_3 = \delta_4 = \operatorname{atan2}(v_y, v_x)$$

All four wheel linear speeds are identical:
$$v_1 = v_2 = v_3 = v_4 = \sqrt{v_x^2 + v_y^2}$$

**Key Advantage:** Allows lateral sidestepping and obstacle circumnavigation without changing orientation.

---

### Mode D: Generalized Swerve Drive (`swerve`)
Mode D computes individual wheel velocities and steering angles for any arbitrary 3-DoF planar body command $\mathbf{V} = [v_x, v_y, \omega_z]^T$.

For each wheel $i$ located at $(x_i, y_i)$:
$$\begin{aligned}
v_{x, i} &= v_x - \omega_z \cdot y_i \\
v_{y, i} &= v_y + \omega_z \cdot x_i
\end{aligned}$$

The target steering angle and linear speed for wheel $i$ are:
$$\delta_i = \operatorname{atan2}(v_{y, i}, v_{x, i})$$
$$v_i = \sqrt{v_{x, i}^2 + v_{y, i}^2}$$

---

### Mode E: Rotation-In-Place (`in_place`)
When turning within a confined footprint without translating ($v_x = 0, v_y = 0, \omega_z \neq 0$), the ICR is located exactly at the geometric origin $(0, 0)$.

Each wheel aligns tangentially to the circle passing through its pivot:
$$\begin{aligned}
\delta_1 (\text{FL}) &= -\operatorname{atan2}\left(\frac{W}{2}, \frac{L}{2}\right) = -45.0^\circ \\
\delta_2 (\text{FR}) &= +\operatorname{atan2}\left(\frac{W}{2}, \frac{L}{2}\right) = +45.0^\circ \\
\delta_3 (\text{RL}) &= +\operatorname{atan2}\left(\frac{W}{2}, \frac{L}{2}\right) = +45.0^\circ \\
\delta_4 (\text{RR}) &= -\operatorname{atan2}\left(\frac{W}{2}, \frac{L}{2}\right) = -45.0^\circ
\end{aligned}$$

All wheel speeds are equal:
$$v_i = \omega_z \cdot \sqrt{(L/2)^2 + (W/2)^2} = \omega_z \cdot R_{diag}$$

---

## 3. Forward Kinematics & Planar Least-Squares Odometry

Given measured knuckle angles $\hat{\delta}_i$ and measured wheel rotational velocities $\hat{\omega}_i$ from `joint_states`, the measured ground velocity vector at each wheel pivot is:

$$\mathbf{v}_i = \begin{bmatrix} v_{x, i} \\ v_{y, i} \end{bmatrix} = \begin{bmatrix} \hat{\omega}_i r \cos(\hat{\delta}_i) \\ \hat{\omega}_i r \sin(\hat{\delta}_i) \end{bmatrix}$$

Each wheel provides two linear equations relating body motion $[v_x, v_y, \omega_z]^T$:
$$\begin{bmatrix} 1 & 0 & -y_i \\ 0 & 1 & +x_i \end{bmatrix} \begin{bmatrix} v_x \\ v_y \\ \omega_z \end{bmatrix} = \begin{bmatrix} v_{x, i} \\ v_{y, i} \end{bmatrix}$$

Stacking all 4 wheels yields an overdetermined linear system of 8 equations in 3 unknowns:
$$\mathbf{A} \begin{bmatrix} v_x \\ v_y \\ \omega_z \end{bmatrix} = \mathbf{b}, \quad \text{where } \mathbf{A} \in \mathbb{R}^{8 \times 3}, \mathbf{b} \in \mathbb{R}^8$$

The optimal, noise-filtered body velocity estimate is solved in closed-form via pseudo-inverse least-squares:
$$\begin{bmatrix} \hat{v}_x \\ \hat{v}_y \\ \hat{\omega}_z \end{bmatrix} = (\mathbf{A}^T \mathbf{A})^{-1} \mathbf{A}^T \mathbf{b}$$

Because the wheels are symmetrically distributed ($\sum x_i = 0, \sum y_i = 0$), $\mathbf{A}^T \mathbf{A}$ is strictly diagonal:
$$\mathbf{A}^T \mathbf{A} = \begin{bmatrix} 4 & 0 & 0 \\ 0 & 4 & 0 \\ 0 & 0 & \sum (x_i^2 + y_i^2) \end{bmatrix}$$

This yields the decoupled, extremely fast closed-form solution:
$$\begin{aligned}
\hat{v}_x &= \frac{1}{4} \sum_{i=1}^4 v_{x, i} \\
\hat{v}_y &= \frac{1}{4} \sum_{i=1}^4 v_{y, i} \\
\hat{\omega}_z &= \frac{\sum_{i=1}^4 (-y_i v_{x, i} + x_i v_{y, i})}{\sum_{i=1}^4 (x_i^2 + y_i^2)}
\end{aligned}$$

Dead-reckoning position $(x, y, \theta)$ is then integrated at 50 Hz using 2nd-order Runge-Kutta integration:
$$\begin{aligned}
\Delta \theta &= \hat{\omega}_z \Delta t \\
\bar{\theta} &= \theta + \frac{\Delta \theta}{2} \\
x &\leftarrow x + (\hat{v}_x \cos\bar{\theta} - \hat{v}_y \sin\bar{\theta}) \Delta t \\
y &\leftarrow y + (\hat{v}_x \sin\bar{\theta} + \hat{v}_y \cos\bar{\theta}) \Delta t \\
\theta &\leftarrow \theta + \Delta \theta
\end{aligned}$$

