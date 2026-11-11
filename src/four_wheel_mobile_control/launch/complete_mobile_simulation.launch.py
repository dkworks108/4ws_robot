#!/usr/bin/env python3
"""
Master Launch File for Project 04: Four-Wheel Steering Autonomous Mobile Robot.

Unified single-command readiness-gated launch orchestrating the complete system:
  Stage 1-4 : Gazebo Fortress + World Validation + Robot Spawn + ros2_control
              (JSB + 4 Steering + 4 Wheel Controllers) + Kinematics/Odom + Sensor Bridges
  Gate SIM  : Verifies /clock, /odom, /scan, /imu/data, 9 active controllers, TF odom->base_footprint
  Stage 5   : SLAM Toolbox online async mapping [if use_slam=true]
  Stage 8   : Command Arbiter, rosbridge, rosapi, web_video_server, web_server [if use_mobile_control=true]
  Stage 9a  : System Readiness & Runtime Health Monitor
  Gate SLAM : Verifies /map and TF map->odom [if use_slam=true]
  Stage 6   : Nav2 stack (remapped to /cmd_vel_nav -> arbiter -> /cmd_vel) [if use_navigation=true]
  Gate NAV2 : Verifies Nav2 lifecycle nodes ACTIVE and navigate_to_pose action ready [if use_navigation=true]
  Stage 7   : Frontier Exploration node [if use_exploration=true]
  Stage 9b  : RViz2 visualization [if use_rviz=true and not headless]
"""

import os
import xml.etree.ElementTree as ET
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
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
    return ""


def validate_sdf_world(world_path: str) -> None:
    """Validate that the selected SDF world exists, parses cleanly, and fits Gazebo Fortress."""
    if not world_path or not os.path.exists(world_path):
        raise RuntimeError(
            f"[WORLD ERROR] World SDF file does not exist: '{world_path}'. "
            "Pass a valid path via world:=PATH_TO_WORLD."
        )
    try:
        tree = ET.parse(world_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        raise RuntimeError(f"[WORLD ERROR] Malformed SDF XML in '{world_path}': {exc}") from exc

    if root.tag != "sdf" or root.find("world") is None:
        raise RuntimeError(
            f"[WORLD ERROR] File '{world_path}' is not a valid SDF world (<sdf>/<world> missing)."
        )

    with open(world_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "libgazebo_ros_" in content:
        raise RuntimeError(
            f"[WORLD ERROR] World '{world_path}' references Gazebo Classic 'libgazebo_ros_*' plugins, "
            "which are incompatible with Gazebo Fortress (Ignition Sim 6)."
        )


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ws_root = os.path.abspath(os.path.join(pkg_dir, "..", ".."))

    def _share(pkg, src_subdir):
        try:
            return get_package_share_directory(pkg)
        except Exception:
            return os.path.join(ws_root, "src", src_subdir)

    desc_share = _share("four_wheel_description", "four_wheel_description")
    nav_share = _share("four_wheel_navigation", "four_wheel_navigation")
    expl_share = _share("four_wheel_exploration", "four_wheel_exploration")
    mob_share = _share("four_wheel_mobile_control", "four_wheel_mobile_control")

    default_world = find_file([
        os.path.join(desc_share, "worlds", "outdoor_proving_ground.sdf"),
        os.path.join(ws_root, "worlds", "outdoor_proving_ground.sdf"),
        os.path.join(ws_root, "src", "four_wheel_description", "worlds", "outdoor_proving_ground.sdf"),
        os.path.join(desc_share, "worlds", "four_wheel_arena.sdf"),
        os.path.join(ws_root, "worlds", "four_wheel_arena.sdf"),
    ])

    slam_params_file = find_file([
        os.path.join(nav_share, "config", "mapper_params_online_async.yaml"),
        os.path.join(ws_root, "src", "four_wheel_navigation", "config", "mapper_params_online_async.yaml"),
    ])

    nav2_params_file = find_file([
        os.path.join(nav_share, "config", "nav2_params.yaml"),
        os.path.join(ws_root, "src", "four_wheel_navigation", "config", "nav2_params.yaml"),
    ])

    explorer_params_file = find_file([
        os.path.join(expl_share, "config", "exploration_params.yaml"),
        os.path.join(ws_root, "src", "four_wheel_exploration", "config", "exploration_params.yaml"),
    ])

    mobile_params_file = find_file([
        os.path.join(mob_share, "config", "mobile_control_params.yaml"),
        os.path.join(ws_root, "src", "four_wheel_mobile_control", "config", "mobile_control_params.yaml"),
    ])

    rviz_config_file = find_file([
        os.path.join(desc_share, "rviz", "four_wheel.rviz"),
        os.path.join(ws_root, "src", "four_wheel_description", "rviz", "four_wheel.rviz"),
    ])

    declared_args = [
        DeclareLaunchArgument(
            "world",
            default_value=default_world,
            description="Full path to the Gazebo Fortress SDF world file",
        ),
        DeclareLaunchArgument(
            "headless",
            default_value="false",
            description="Run Gazebo in headless server mode (no GUI)",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Launch RViz2 desktop visualization (skipped when headless=true)",
        ),
        DeclareLaunchArgument(
            "use_slam",
            default_value="true",
            description="Launch SLAM Toolbox online async mapping",
        ),
        DeclareLaunchArgument(
            "use_navigation",
            default_value="true",
            description="Launch Nav2 autonomous navigation stack",
        ),
        DeclareLaunchArgument(
            "use_exploration",
            default_value="true",
            description="Launch autonomous frontier exploration node",
        ),
        DeclareLaunchArgument(
            "use_mobile_control",
            default_value="true",
            description="Launch mobile web server, rosbridge, command arbiter, and video server",
        ),
        DeclareLaunchArgument(
            "use_camera",
            default_value="true",
            description="Enable RGB camera bridge and web video streaming",
        ),
        DeclareLaunchArgument(
            "camera_width",
            default_value="640",
            description="RGB camera image width in pixels",
        ),
        DeclareLaunchArgument(
            "camera_height",
            default_value="480",
            description="RGB camera image height in pixels",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation clock (/clock) for all nodes",
        ),
        DeclareLaunchArgument(
            "exploration_autostart",
            default_value="false",
            description="Automatically dispatch exploration goals on startup",
        ),
        DeclareLaunchArgument(
            "web_port",
            default_value="3000",
            description="TCP port for the mobile dashboard HTTP server",
        ),
        DeclareLaunchArgument(
            "rosbridge_port",
            default_value="9090",
            description="TCP port for the Rosbridge WebSocket server",
        ),
        DeclareLaunchArgument(
            "video_port",
            default_value="8080",
            description="TCP port for the Web Video Server (MJPEG camera stream)",
        ),
    ]

    def _build_staged_actions(context):
        def _flag(name: str) -> bool:
            return LaunchConfiguration(name).perform(context).strip().lower() == "true"

        world_path = LaunchConfiguration("world").perform(context)
        validate_sdf_world(world_path)

        headless = _flag("headless")
        use_rviz = _flag("use_rviz") and not headless
        use_slam = _flag("use_slam")
        use_nav = _flag("use_navigation")
        use_expl = _flag("use_exploration")
        use_mobile = _flag("use_mobile_control")
        use_camera = _flag("use_camera")
        use_sim_time = _flag("use_sim_time")
        expl_autostart = LaunchConfiguration("exploration_autostart").perform(context)
        cam_w = LaunchConfiguration("camera_width").perform(context)
        cam_h = LaunchConfiguration("camera_height").perform(context)
        web_port = int(LaunchConfiguration("web_port").perform(context))
        rosbridge_port = int(LaunchConfiguration("rosbridge_port").perform(context))
        video_port = int(LaunchConfiguration("video_port").perform(context))

        # --------------------------------------------------------------
        # STAGE 1-4: Simulation, Robot, Controllers, Kinematics, Sensors
        # --------------------------------------------------------------
        stage1_gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(desc_share, "launch", "gazebo.launch.py")
            ),
            launch_arguments={
                "world": world_path,
                "headless": "true" if headless else "false",
                "use_sim_time": "true" if use_sim_time else "false",
                "rviz": "false",
                "use_camera": "true" if use_camera else "false",
                "camera_width": cam_w,
                "camera_height": cam_h,
            }.items(),
        )

        # Gate A: Wait for Simulation + 9 Controllers + Kinematics/Odom + Sensors + TF
        gate_sim = ExecuteProcess(
            cmd=[
                "ros2", "run", "four_wheel_mobile_control", "launch_gate",
                "--stage", "sim", "--timeout", "45.0",
                "--ros-args", "-p", f"use_sim_time:={'true' if use_sim_time else 'false'}",
            ],
            name="launch_gate_sim",
            output="screen",
        )

        # Helper builders for later stages
        def _make_mobile_and_readiness_actions():
            actions = []
            if use_mobile:
                arbiter_params = [{"use_sim_time": use_sim_time}]
                if mobile_params_file and os.path.exists(mobile_params_file):
                    arbiter_params.insert(0, mobile_params_file)

                web_params = [{
                    "port": web_port,
                    "rosbridge_port": rosbridge_port,
                    "web_video_port": video_port,
                    "use_sim_time": use_sim_time,
                }]
                if mobile_params_file and os.path.exists(mobile_params_file):
                    web_params.insert(0, mobile_params_file)

                actions.extend([
                    LogInfo(msg="[STAGE 8] Starting Mobile Stack (arbiter, rosbridge, rosapi, web_server, video_server)..."),
                    Node(
                        package="rosbridge_server",
                        executable="rosbridge_websocket",
                        name="rosbridge_websocket",
                        output="screen",
                        parameters=[{
                            "port": rosbridge_port,
                            "address": "0.0.0.0",
                            "call_services_in_new_thread": True,
                            "send_action_goals_in_new_thread": True,
                            "default_call_service_timeout": 5.0,
                            "use_sim_time": use_sim_time,
                        }],
                    ),
                    Node(
                        package="rosapi",
                        executable="rosapi_node",
                        name="rosapi",
                        output="screen",
                        parameters=[{"use_sim_time": use_sim_time}],
                    ),
                    Node(
                        package="four_wheel_mobile_control",
                        executable="command_arbiter_node",
                        name="command_arbiter_node",
                        output="screen",
                        parameters=arbiter_params,
                    ),
                    Node(
                        package="four_wheel_mobile_control",
                        executable="web_server",
                        name="mobile_dashboard_web_server",
                        output="screen",
                        parameters=web_params,
                    ),
                ])
                if use_camera:
                    actions.append(
                        Node(
                            package="web_video_server",
                            executable="web_video_server",
                            name="web_video_server",
                            output="screen",
                            parameters=[{
                                "port": video_port,
                                "address": "0.0.0.0",
                                "use_sim_time": use_sim_time,
                            }],
                        )
                    )

            actions.append(
                Node(
                    package="four_wheel_mobile_control",
                    executable="system_readiness_node",
                    name="system_readiness_node",
                    output="screen",
                    parameters=[{
                        "use_sim_time": use_sim_time,
                        "require_gazebo": True,
                        "require_robot": True,
                        "require_controllers": True,
                        "require_kinematics": True,
                        "require_odom": True,
                        "require_lidar": True,
                        "require_imu": True,
                        "require_camera": use_camera,
                        "require_tf": True,
                        "require_slam": use_slam,
                        "require_nav2": use_nav,
                        "require_exploration": use_expl,
                        "require_arbiter": use_mobile,
                        "require_rosbridge": use_mobile,
                        "require_dashboard": use_mobile,
                        "require_video_server": use_mobile and use_camera,
                        "web_port": web_port,
                        "rosbridge_port": rosbridge_port,
                        "video_port": video_port,
                        "timeout_sec": 90.0,
                    }],
                )
            )
            return actions

        def _make_exploration_and_rviz_actions():
            actions = []
            if use_expl:
                expl_autostart_bool = expl_autostart.strip().lower() not in ("false", "0", "no", "")
                expl_params = [{
                    "use_sim_time": use_sim_time,
                    "autostart": expl_autostart_bool,
                }]
                if explorer_params_file and os.path.exists(explorer_params_file):
                    expl_params.insert(0, explorer_params_file)
                actions.append(LogInfo(msg="[STAGE 7] Starting Frontier Exploration node..."))
                actions.append(
                    Node(
                        package="four_wheel_exploration",
                        executable="explorer_node",
                        name="explorer_node",
                        output="screen",
                        parameters=expl_params,
                    )
                )
            if use_rviz:
                actions.append(LogInfo(msg="[STAGE 9] Starting RViz2 desktop visualization..."))
                actions.append(
                    Node(
                        package="rviz2",
                        executable="rviz2",
                        name="rviz2",
                        output="screen",
                        arguments=["-d", rviz_config_file] if rviz_config_file else [],
                        parameters=[{"use_sim_time": use_sim_time}],
                    )
                )
            return actions

        def _make_nav2_actions_and_gate():
            nav_launch_args = {
                "use_sim_time": "true" if use_sim_time else "false",
                "cmd_vel_topic": "/cmd_vel_nav" if use_mobile else "/cmd_vel",
            }
            if nav2_params_file and os.path.exists(nav2_params_file):
                nav_launch_args["params_file"] = nav2_params_file

            nav_include = IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav_share, "launch", "navigation.launch.py")
                ),
                launch_arguments=nav_launch_args.items(),
            )
            gate_nav2 = ExecuteProcess(
                cmd=[
                    "ros2", "run", "four_wheel_mobile_control", "launch_gate",
                    "--stage", "nav2", "--timeout", "45.0",
                    "--ros-args", "-p", f"use_sim_time:={'true' if use_sim_time else 'false'}",
                ],
                name="launch_gate_nav2",
                output="screen",
            )

            def _on_nav2_gate_exit(event, _ctx):
                if event.returncode != 0:
                    return [LogInfo(msg="[CRITICAL FAILURE] Nav2 readiness gate failed; skipping Exploration startup.")]
                return _make_exploration_and_rviz_actions()

            return [
                LogInfo(msg="[STAGE 6] Starting Nav2 autonomous navigation stack..."),
                nav_include,
                gate_nav2,
                RegisterEventHandler(
                    OnProcessExit(target_action=gate_nav2, on_exit=_on_nav2_gate_exit)
                ),
            ]

        def _on_sim_gate_exit(event, _ctx):
            if event.returncode != 0:
                return [
                    LogInfo(msg="[CRITICAL FAILURE] Simulation/Controller readiness gate failed; halting dependent stages.")
                ]

            actions = _make_mobile_and_readiness_actions()
            if use_slam:
                slam_args = {"use_sim_time": "true" if use_sim_time else "false"}
                if slam_params_file and os.path.exists(slam_params_file):
                    slam_args["params_file"] = slam_params_file

                slam_include = IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(nav_share, "launch", "slam.launch.py")
                    ),
                    launch_arguments=slam_args.items(),
                )
                gate_slam = ExecuteProcess(
                    cmd=[
                        "ros2", "run", "four_wheel_mobile_control", "launch_gate",
                        "--stage", "slam", "--timeout", "35.0",
                        "--ros-args", "-p", f"use_sim_time:={'true' if use_sim_time else 'false'}",
                    ],
                    name="launch_gate_slam",
                    output="screen",
                )

                def _on_slam_gate_exit(slam_ev, _ctx2):
                    if slam_ev.returncode != 0:
                        return [LogInfo(msg="[CRITICAL FAILURE] SLAM readiness gate failed; halting Nav2/Exploration.")]
                    if use_nav:
                        return _make_nav2_actions_and_gate()
                    return _make_exploration_and_rviz_actions()

                actions.extend([
                    LogInfo(msg="[STAGE 5] Starting SLAM Toolbox online mapping..."),
                    slam_include,
                    gate_slam,
                    RegisterEventHandler(
                        OnProcessExit(target_action=gate_slam, on_exit=_on_slam_gate_exit)
                    ),
                ])
            elif use_nav:
                actions.extend(_make_nav2_actions_and_gate())
            else:
                actions.extend(_make_exploration_and_rviz_actions())

            return actions

        return [
            LogInfo(msg=f"[STAGE 1] Validated world SDF: {world_path}"),
            stage1_gazebo,
            gate_sim,
            RegisterEventHandler(
                OnProcessExit(target_action=gate_sim, on_exit=_on_sim_gate_exit)
            ),
        ]

    return LaunchDescription(declared_args + [OpaqueFunction(function=_build_staged_actions)])
