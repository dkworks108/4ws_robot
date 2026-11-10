import os
import subprocess
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
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

    ctrl_share = ""
    try:
        ctrl_share = get_package_share_directory('four_wheel_control')
    except Exception:
        pass

    xacro_path = find_file([
        os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro'),
        os.path.join(ws_root, 'src', 'four_wheel_description', 'urdf', 'robot.urdf.xacro'),
        os.path.join(pkg_dir, 'urdf', 'robot.urdf.xacro')
    ])

    controllers_yaml = find_file([
        os.path.join(ctrl_share, 'config', 'ros2_controllers.yaml'),
        os.path.join(ws_root, 'src', 'four_wheel_control', 'config', 'ros2_controllers.yaml'),
        os.path.join(ws_root, 'config', 'ros2_controllers.yaml')
    ])

    default_world = find_file([
        os.path.join(pkg_share, 'worlds', 'four_wheel_arena.sdf'),
        os.path.join(ws_root, 'worlds', 'four_wheel_arena.sdf'),
        os.path.join(ws_root, 'src', 'four_wheel_description', 'worlds', 'four_wheel_arena.sdf')
    ])

    rviz_config = find_file([
        os.path.join(pkg_share, 'rviz', 'four_wheel.rviz'),
        os.path.join(ws_root, 'src', 'four_wheel_description', 'rviz', 'four_wheel.rviz'),
        os.path.join(ws_root, 'config', 'rviz.rviz')
    ])

    declared_args = [
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='Run Gazebo Fortress in headless mode (server only)'
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='false',
            description='Launch RViz2 alongside Gazebo Fortress'
        ),
        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='Full path to Gazebo SDF world file'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock'
        ),
        DeclareLaunchArgument(
            'x',
            default_value='0.0',
            description='Initial robot spawn X position'
        ),
        DeclareLaunchArgument(
            'y',
            default_value='0.0',
            description='Initial robot spawn Y position'
        ),
        DeclareLaunchArgument(
            'z',
            default_value='0.08',
            description='Initial robot spawn Z position'
        )
    ]

    headless_arg = LaunchConfiguration('headless')
    rviz_arg = LaunchConfiguration('rviz')
    world_arg = LaunchConfiguration('world')
    use_sim_time = LaunchConfiguration('use_sim_time')
    spawn_x = LaunchConfiguration('x')
    spawn_y = LaunchConfiguration('y')
    spawn_z = LaunchConfiguration('z')

    # Generate robot description from xacro
    robot_desc = subprocess.check_output([
        'xacro', xacro_path,
        f'controllers_yaml:={controllers_yaml}'
    ]).decode('utf-8')

    # 1. Robot State Publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': use_sim_time
        }]
    )

    # 2. Gazebo Fortress (Ignition) Launch
    ros_gz_sim_dir = get_package_share_directory('ros_gz_sim')
    gz_args = PythonExpression([
        "'-s -r ' + '", world_arg, "' if '", headless_arg, "' == 'true' else '-r ' + '", world_arg, "'"
    ])

    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_dir, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': gz_args}.items()
    )

    # 3. Spawn entity into Gazebo
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_four_wheel_robot',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'four_wheel_steering_robot',
            '-x', spawn_x,
            '-y', spawn_y,
            '-z', spawn_z
        ]
    )

    # 4. ROS-Gazebo Parameter Bridge
    bridge_params = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='parameter_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/imu/data@sensor_msgs/msg/Imu[ignition.msgs.IMU',
            '/camera/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image'
        ]
    )

    # 5. Controller Spawners
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    steering_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['steering_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['drive_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    # Sequencing: joint_state_broadcaster -> steering_controller -> drive_controller
    delay_steering_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[steering_controller_spawner]
        )
    )

    delay_drive_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=steering_controller_spawner,
            on_exit=[drive_controller_spawner]
        )
    )

    # 6. Four-Wheel Kinematics & Odometry Node
    kinematics_node = Node(
        package='four_wheel_control',
        executable='four_wheel_kinematics_node',
        name='four_wheel_kinematics_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'default_mode': 'four_wheel_steer',
            'wheelbase': 0.36,
            'track_width': 0.36,
            'wheel_radius': 0.08,
            'max_steering_angle': 1.5707963,
            'max_wheel_speed': 25.0,
            'cmd_vel_timeout': 0.5,
            'publish_tf': True
        }]
    )

    # 7. RViz2 (optional)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz_arg)
    )

    return LaunchDescription(
        declared_args + [
            node_robot_state_publisher,
            gz_sim_launch,
            spawn_entity,
            bridge_params,
            joint_state_broadcaster_spawner,
            delay_steering_controller,
            delay_drive_controller,
            kinematics_node,
            rviz_node
        ]
    )
