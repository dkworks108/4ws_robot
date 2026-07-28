# 4ws robot

four wheel independent steering chassis.

each corner has 2 joints:
1. steering joint (revolute, rotates around z axis to steer the wheel)
2. wheel spin joint (continuous, spins around y axis)

total 8 joints for the wheels.
all 4 corners are symmetric so it can do crab walking or zero radius turns.

run rviz:
ros2 launch launch/display.launch.py
