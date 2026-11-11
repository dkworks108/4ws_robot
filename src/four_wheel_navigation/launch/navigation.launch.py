import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_nav2_params = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    try:
        pkg_share = get_package_share_directory('four_wheel_navigation')
        default_nav2_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    except Exception:
        pass

    # Find bt xml
    bt_xml = ""
    try:
        bt_share = get_package_share_directory('nav2_bt_navigator')
        bt_xml = os.path.join(bt_share, 'behavior_trees', 'navigate_to_pose_w_replanning_and_recovery.xml')
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
            default_value=default_nav2_params,
            description='Path to Nav2 params yaml'
        ),
        DeclareLaunchArgument(
            'cmd_vel_topic',
            default_value='/cmd_vel',
            description='Output topic for controller and behavior velocity commands'
        )
    ]

    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    cmd_vel_topic = LaunchConfiguration('cmd_vel_topic')

    bt_params = [params_file, {'use_sim_time': use_sim_time}]
    if bt_xml and os.path.exists(bt_xml):
        bt_params.append({'default_nav_to_pose_bt_xml': bt_xml})

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}],
        remappings=[('cmd_vel', cmd_vel_topic)]
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}]
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}],
        remappings=[('cmd_vel', cmd_vel_topic)]
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=bt_params,
        remappings=[('cmd_vel', cmd_vel_topic)]
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': True},
            {'node_names': ['controller_server', 'planner_server', 'behavior_server', 'bt_navigator']}
        ]
    )

    return LaunchDescription(
        declared_args + [
            controller_server,
            planner_server,
            behavior_server,
            bt_navigator,
            lifecycle_manager
        ]
    )
