from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'default_mode',
            default_value='four_wheel_steer',
            description='Initial steering mode (front_steer, four_wheel_steer, crab, generalized, in_place_spin)'
        )
    ]

    use_sim_time = LaunchConfiguration('use_sim_time')
    default_mode = LaunchConfiguration('default_mode')

    kinematics_node = Node(
        package='four_wheel_control',
        executable='four_wheel_kinematics_node',
        name='four_wheel_kinematics_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'default_mode': default_mode,
            'wheelbase': 0.36,
            'track_width': 0.36,
            'wheel_radius': 0.08,
            'max_steering_angle': 1.5707963,
            'max_wheel_speed': 25.0,
            'cmd_vel_timeout': 0.5,
            'publish_tf': True
        }]
    )

    return LaunchDescription(declared_args + [kinematics_node])

