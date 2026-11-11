import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def find_file(candidates):
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return candidates[0] if candidates else ""


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"

    pkg_share = ""
    try:
        pkg_share = get_package_share_directory('four_wheel_description')
    except Exception:
        pass

    nav_share = ""
    try:
        nav_share = get_package_share_directory('four_wheel_navigation')
    except Exception:
        pass

    expl_share = ""
    try:
        expl_share = get_package_share_directory('four_wheel_exploration')
    except Exception:
        pass

    desc_dir = find_file([
        pkg_share,
        os.path.join(ws_root, 'src', 'four_wheel_description'),
        pkg_dir
    ])

    nav_dir = find_file([
        nav_share,
        os.path.join(ws_root, 'src', 'four_wheel_navigation')
    ])

    expl_dir = find_file([
        expl_share,
        os.path.join(ws_root, 'src', 'four_wheel_exploration')
    ])

    default_world = find_file([
        os.path.join(pkg_share, 'worlds', 'four_wheel_arena.sdf'),
        os.path.join(ws_root, 'worlds', 'four_wheel_arena.sdf'),
        os.path.join(ws_root, 'src', 'four_wheel_description', 'worlds', 'four_wheel_arena.sdf')
    ])

    slam_params_file = find_file([
        os.path.join(nav_share, 'config', 'mapper_params_online_async.yaml'),
        os.path.join(ws_root, 'src', 'four_wheel_navigation', 'config', 'mapper_params_online_async.yaml')
    ])

    nav2_params_file = find_file([
        os.path.join(nav_share, 'config', 'nav2_params.yaml'),
        os.path.join(ws_root, 'src', 'four_wheel_navigation', 'config', 'nav2_params.yaml')
    ])

    declared_args = [
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='Run Gazebo in headless mode'
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='true',
            description='Launch RViz2 visualization'
        ),
        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='Gazebo SDF world file path'
        ),
        DeclareLaunchArgument(
            'slam',
            default_value='true',
            description='Launch SLAM Toolbox mapping'
        ),
        DeclareLaunchArgument(
            'navigation',
            default_value='true',
            description='Launch Nav2 autonomous navigation'
        ),
        DeclareLaunchArgument(
            'exploration',
            default_value='true',
            description='Launch autonomous frontier exploration'
        ),
        DeclareLaunchArgument(
            'exploration_autostart',
            default_value='true',
            description='Automatically begin dispatching exploration goals'
        ),
        DeclareLaunchArgument(
            'cmd_vel_topic',
            default_value='/cmd_vel',
            description='Output velocity topic for Nav2 controller'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock'
        )
    ]

    headless_arg = LaunchConfiguration('headless')
    rviz_arg = LaunchConfiguration('rviz')
    world_arg = LaunchConfiguration('world')
    slam_arg = LaunchConfiguration('slam')
    navigation_arg = LaunchConfiguration('navigation')
    exploration_arg = LaunchConfiguration('exploration')
    exploration_autostart = LaunchConfiguration('exploration_autostart')
    cmd_vel_topic = LaunchConfiguration('cmd_vel_topic')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # 1. Gazebo Fortress + Controllers + Robot State Publisher + Bridge
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(desc_dir, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'headless': headless_arg,
            'rviz': rviz_arg,
            'world': world_arg,
            'use_sim_time': use_sim_time
        }.items()
    )

    # 2. SLAM Toolbox (conditioned on slam=true)
    slam_launch = TimerAction(
        period=4.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav_dir, 'launch', 'slam.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'params_file': slam_params_file
                }.items(),
                condition=IfCondition(slam_arg)
            )
        ]
    )

    # 3. Nav2 Navigation (conditioned on navigation=true)
    nav_launch = TimerAction(
        period=7.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav_dir, 'launch', 'navigation.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'params_file': nav2_params_file,
                    'cmd_vel_topic': cmd_vel_topic
                }.items(),
                condition=IfCondition(navigation_arg)
            )
        ]
    )

    # 4. Frontier Explorer Node (conditioned on exploration=true)
    explorer_params = os.path.join(expl_dir, 'config', 'exploration_params.yaml')
    explorer_launch = TimerAction(
        period=12.0,
        actions=[
            Node(
                package='four_wheel_exploration',
                executable='explorer_node',
                name='explorer_node',
                output='screen',
                parameters=[
                    explorer_params,
                    {
                        'use_sim_time': use_sim_time,
                        'autostart': exploration_autostart
                    }
                ],
                condition=IfCondition(exploration_arg)
            )
        ]
    )

    return LaunchDescription(
        declared_args + [
            gazebo_launch,
            slam_launch,
            nav_launch,
            explorer_launch
        ]
    )
