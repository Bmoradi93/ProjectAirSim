# Run these targets from INSIDE the dev/ros2 containers (see docker-compose.yml / docs/docker.md).
SHELL := /bin/bash
SCENE_CONFIG ?= scene_px4_sitl.jsonc
SIM_CONFIG_PATH ?= /workspace/ProjectAirSim/client/python/example_user_scripts/sim_config
FCU_URL ?= udp://:14550@127.0.0.1:18570

.PHONY: help editor game ros2-bridge-build ros2-bridge ros2-build ros2-ws-build mavros rviz

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

editor: ## Launch the Unreal Editor (Blocks project)
	$(UE_ROOT)/Engine/Binaries/Linux/UnrealEditor /workspace/ProjectAirSim/unreal/Blocks/Blocks.uproject

game: ## Launch the Unreal Blocks project directly in Game mode
	$(UE_ROOT)/Engine/Binaries/Linux/UnrealEditor /workspace/ProjectAirSim/unreal/Blocks/Blocks.uproject -game

ros2-build ros2-ws-build: ## Build ros2_workspace (optional: make ros2-build PKG=<package_name>)
	source /opt/ros/humble/setup.bash && \
	if [ -f /workspace/ProjectAirSim/ros2_workspace/install/setup.bash ]; then source /workspace/ProjectAirSim/ros2_workspace/install/setup.bash; fi && \
	cd /workspace/ProjectAirSim/ros2_workspace && \
	colcon build $(if $(PKG),--packages-select $(PKG),) --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF

ros2-bridge-build: ## Build only projectairsim_ros2_cpp in ros2_workspace
	$(MAKE) ros2-build PKG=projectairsim_ros2_cpp

ros2-bridge: ## Run projectairsim_ros2_cpp_node (loads SCENE_CONFIG, default: scene_px4_sitl.jsonc)
	source /opt/ros/humble/setup.bash && \
	source /workspace/ProjectAirSim/ros2_workspace/install/setup.bash && \
	ros2 run projectairsim_ros2_cpp projectairsim_ros2_cpp_node --ros-args \
		-p scene_config:=$(SCENE_CONFIG) \
		-p sim_config_path:=$(SIM_CONFIG_PATH)

mavros: ## Launch ROS 2 MAVROS connected to PX4 SITL (override with FCU_URL=...)
	source /opt/ros/humble/setup.bash && \
	source /workspace/ProjectAirSim/ros2_workspace/install/setup.bash && \
	ros2 launch mavros px4.launch fcu_url:=$(FCU_URL)

rviz: ## Launch RViz2 pre-configured with Drone1 Cameras, LiDAR (Best Effort QoS), and TF
	source /opt/ros/humble/setup.bash && \
	rviz2 -d /workspace/ProjectAirSim/ros2_workspace/src/projectairsim_ros2_cpp/config/px4_drone.rviz
