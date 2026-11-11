import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import AnyLaunchDescriptionSource, PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def find_file(candidates):
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return candidates[0] if candidates else ""


def generate_launch_description():
    ws_root = "/media/bumble/DATA_DISK/robotics/projects/04_four_wheel_steering"

    try:
        pkg_share = get_package_share_directory('four_wheel_mobile_control')
    except Exception:
        pkg_share = os.path.join(ws_root, 'src', 'four_wheel_mobile_control')

    default_params = find_file([
        os.path.join(pkg_share, 'config', 'mobile_control_params.yaml'),
        os.path.join(ws_root, 'src', 'four_wheel_mobile_control', 'config', 'mobile_control_params.yaml')
    ])

    declared_args = [
        DeclareLaunchArgument(
            'web_port',
            default_value='3000',
            description='Port for HTTP Web Server serving mobile dashboard'
        ),
        DeclareLaunchArgument(
            'rosbridge_port',
            default_value='9090',
            description='Port for Rosbridge WebSocket server'
        ),
        DeclareLaunchArgument(
            'video_port',
            default_value='8080',
            description='Port for Web Video Server (Camera stream)'
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Configuration YAML file for mobile control'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock'
        )
    ]

    web_port = LaunchConfiguration('web_port')
    rosbridge_port = LaunchConfiguration('rosbridge_port')
    video_port = LaunchConfiguration('video_port')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # 1. Rosbridge WebSocket Server
    rosbridge_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='screen',
        parameters=[{
            'port': 9090,
            'address': '0.0.0.0',
            'call_services_in_new_thread': True,
            'send_action_goals_in_new_thread': True,
            'default_call_service_timeout': 5.0,
            'use_sim_time': use_sim_time
        }]
    )

    # 2. Rosapi Node (service reflection for roslibjs)
    rosapi_node = Node(
        package='rosapi',
        executable='rosapi_node',
        name='rosapi',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # 3. Web Video Server for Camera MJPEG Streaming
    web_video_node = Node(
        package='web_video_server',
        executable='web_video_server',
        name='web_video_server',
        output='screen',
        parameters=[{
            'port': 8080,
            'address': '0.0.0.0',
            'use_sim_time': use_sim_time
        }]
    )

    # 4. Command Arbiter & Safety Multiplexer
    arbiter_node = Node(
        package='four_wheel_mobile_control',
        executable='command_arbiter_node',
        name='command_arbiter_node',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}]
    )

    # 5. Mobile Dashboard Web Server (port 3000)
    web_server_node = Node(
        package='four_wheel_mobile_control',
        executable='web_server',
        name='mobile_dashboard_web_server',
        output='screen',
        parameters=[
            params_file,
            {
                'port': 3000,
                'rosbridge_port': 9090,
                'web_video_port': 8080,
                'use_sim_time': use_sim_time
            }
        ]
    )

    return LaunchDescription(
        declared_args + [
            rosbridge_node,
            rosapi_node,
            web_video_node,
            arbiter_node,
            web_server_node
        ]
    )

