from glob import glob
import os
from setuptools import find_packages, setup

package_name = "efferax_launcher"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ProjectAirSim Dev",
    maintainer_email="dev@projectairsim.local",
    description="Master bringup launch package for the Efferax PX4 + MAVROS + Project AirSim autonomy stack.",
    license="MIT",
    entry_points={
        "console_scripts": [],
    },
)
