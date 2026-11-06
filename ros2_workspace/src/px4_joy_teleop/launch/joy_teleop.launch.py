import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("px4_joy_teleop")
    default_config = os.path.join(pkg_share, "config", "logitech_gamepad.yaml")

    config_file_arg = DeclareLaunchArgument(
        "config_file",
        default_value=default_config,
        description="Path to the gamepad teleop YAML configuration file.",
    )
    control_mode_arg = DeclareLaunchArgument(
        "control_mode",
        default_value="offboard_velocity",
        description="Control mode: 'offboard_velocity' (/setpoint_raw/local) or 'manual_control' (/manual_control/send).",
    )

    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        output="screen",
        parameters=[LaunchConfiguration("config_file")],
    )

    teleop_node = Node(
        package="px4_joy_teleop",
        executable="joy_teleop_node",
        name="px4_joy_teleop_node",
        output="screen",
        parameters=[
            LaunchConfiguration("config_file"),
            {"control_mode": LaunchConfiguration("control_mode")},
        ],
    )

    return LaunchDescription(
        [
            config_file_arg,
            control_mode_arg,
            joy_node,
            teleop_node,
        ]
    )
