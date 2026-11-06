from glob import glob
import os
from setuptools import find_packages, setup

package_name = "px4_joy_teleop"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ProjectAirSim Dev",
    maintainer_email="dev@projectairsim.local",
    description="Gamepad/joystick teleoperation node for PX4 via MAVROS topics and services.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "joy_teleop_node = px4_joy_teleop.joy_teleop_node:main",
        ],
    },
)
