import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import (
    AnyLaunchDescriptionSource,
    PythonLaunchDescriptionSource,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    mavros_share = get_package_share_directory("mavros")
    joy_teleop_share = get_package_share_directory("px4_joy_teleop")

    default_rviz_config = (
        "/workspace/ProjectAirSim/ros2_workspace/src/projectairsim_ros2_cpp/config/px4_drone.rviz"
    )
    default_sim_config_path = (
        "/workspace/ProjectAirSim/client/python/example_user_scripts/sim_config"
    )

    # Launch arguments
    use_sim_bridge_arg = DeclareLaunchArgument(
        "use_sim_bridge",
        default_value="true",
        description="Launch Project AirSim ROS 2 C++ bridge (set to 'false' on real drone hardware).",
    )
    scene_config_arg = DeclareLaunchArgument(
        "scene_config",
        default_value="scene_px4_sitl.jsonc",
        description="Project AirSim scene config file to load.",
    )
    sim_config_path_arg = DeclareLaunchArgument(
        "sim_config_path",
        default_value=default_sim_config_path,
        description="Directory containing Project AirSim JSONC configs.",
    )
    use_mavros_arg = DeclareLaunchArgument(
        "use_mavros",
        default_value="true",
        description="Launch MAVROS PX4 bridge.",
    )
    fcu_url_arg = DeclareLaunchArgument(
        "fcu_url",
        default_value="udp://:14550@127.0.0.1:18570",
        description="MAVROS FCU connection URL (UDP for SITL, serial e.g. /dev/ttyACM0:57600 for real PX4).",
    )
    gcs_url_arg = DeclareLaunchArgument(
        "gcs_url",
        default_value="",
        description="Optional MAVROS GCS proxy URL (e.g. udp://@127.0.0.1:14551).",
    )
    use_joy_arg = DeclareLaunchArgument(
        "use_joy",
        default_value="true",
        description="Launch gamepad teleop nodes (joy_node + px4_joy_teleop_node).",
    )
    control_mode_arg = DeclareLaunchArgument(
        "control_mode",
        default_value="offboard_velocity",
        description="Gamepad teleop mode: 'offboard_velocity' or 'manual_control'.",
    )
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Launch RViz2 visualization.",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_rviz_config,
        description="Path to RViz2 config file.",
    )

    # 1. Project AirSim ROS 2 C++ Bridge (Simulation only)
    projectairsim_bridge_node = Node(
        package="projectairsim_ros2_cpp",
        executable="projectairsim_ros2_cpp_node",
        name="projectairsim_ros2_cpp_node",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_sim_bridge")),
        parameters=[
            {
                "scene_config": LaunchConfiguration("scene_config"),
                "sim_config_path": LaunchConfiguration("sim_config_path"),
            }
        ],
    )

    # 2. MAVROS (PX4 flight controller interface)
    mavros_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(mavros_share, "launch", "px4.launch")
        ),
        condition=IfCondition(LaunchConfiguration("use_mavros")),
        launch_arguments={
            "fcu_url": LaunchConfiguration("fcu_url"),
            "gcs_url": LaunchConfiguration("gcs_url"),
        }.items(),
    )

    # 3. Gamepad Teleop (joy_node + px4_joy_teleop_node)
    joy_teleop_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(joy_teleop_share, "launch", "joy_teleop.launch.py")
        ),
        condition=IfCondition(LaunchConfiguration("use_joy")),
        launch_arguments={
            "control_mode": LaunchConfiguration("control_mode"),
        }.items(),
    )

    # 4. RViz2 Visualization
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_rviz")),
        arguments=["-d", LaunchConfiguration("rviz_config")],
    )

    return LaunchDescription(
        [
            use_sim_bridge_arg,
            scene_config_arg,
            sim_config_path_arg,
            use_mavros_arg,
            fcu_url_arg,
            gcs_url_arg,
            use_joy_arg,
            control_mode_arg,
            use_rviz_arg,
            rviz_config_arg,
            projectairsim_bridge_node,
            mavros_launch,
            joy_teleop_launch,
            rviz_node,
        ]
    )
