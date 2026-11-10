import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_slam_params = os.path.join(pkg_dir, 'config', 'mapper_params_online_async.yaml')

    try:
        pkg_share = get_package_share_directory('four_wheel_navigation')
        default_slam_params = os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml')
    except Exception:
        pass

    declared_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock'
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_slam_params,
            description='Path to SLAM Toolbox configuration file'
        )
    ]

    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}]
    )

    return LaunchDescription(declared_args + [slam_node])
