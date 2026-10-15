# Project AirSim Mastery Course

**A structured curriculum for robotics software engineers learning Unreal Engine–based simulation with ROS 2**

> Target audience: engineers comfortable with Python/C++ and basic ROS 2 who want to become
> productive in Project AirSim for drone/UGV simulation, sensor pipelines, autopilot integration,
> and autonomy development.
>
> Every lesson references real files in this repository. Nothing here is hypothetical.

---

## How to Use This Course

- **Duration**: ~8 weeks at 10–15 hours/week, or self-paced.
- **Format**: Each module has learning objectives, reading, hands-on labs, and a checkpoint project.
- **Hosts**: Modules 0–3 run on the **headless Runtime** (no GPU needed). Modules 4+ require **Unreal Engine 5**.
- **Track your progress**: Copy the checklist at the bottom into your notes.

```
Module 0  Orientation & Mental Model          ──┐
Module 1  Environment & First Flight            │  Headless Runtime
Module 2  Configuration System Deep Dive        │  (no Unreal needed)
Module 3  Python Client API & Control         ──┘
Module 4  Unreal Engine Host & Rendering      ──┐
Module 5  Sensors: Cameras, LiDAR, Radar        │
Module 6  Physics Engines & Vehicle Types       │  Unreal Engine 5
Module 7  Flight Controllers: PX4 & ArduPilot   │  required
Module 8  ROS 2 Integration                     │
Module 9  Advanced Sim: Clocks, Weather, GIS    │
Module 10 Autonomy, Data Collection & ML      ──┘
Module 11 Extending the Simulator (C++)
Module 12 Capstone Projects
```

---

## Module 0 — Orientation & Mental Model

**Goal**: Understand what Project AirSim is, how it differs from AirSim v1, and how the pieces fit together.

### Learning Objectives
- Explain the three-layer architecture: SimLibs (C++ core) → Host (Runtime or Unreal plugin) → Client (Python/C++/ROS).
- Identify which simulation host you need for a given task.
- Know the communication model: msgpack-over-NNG RPC on ports 8989 (topics) and 8990 (services).

### Reading
| Resource | Why |
|---|---|
| `README.md` | Project overview, capabilities, starting points |
| `Architecture.md` | Full system diagrams, startup sequence, data flow |
| `docs/transition_from_airsim.md` | If you know AirSim v1, this maps old concepts to new |
| `docs/faq.md` | Common questions |
| `samples/projectairsim_runtime/README.md` | What the headless host can and cannot do |

### Key Concepts to Internalize
1. **SimLibs** (`core_sim/`, `physics/`, `vehicle_apis/`, `simserver/`, `mavlinkcom/`) are engine-independent C++ libraries. They own the simulation loop, physics, controllers, and the RPC server.
2. **Hosts** embed SimLibs:
   - `projectairsim-runtime` — headless, flat ground, no rendering.
   - Unreal `Blocks` project via `unreal/Blocks/Plugins/ProjectAirSim/` — rendering, meshes, rendered sensors.
3. **Clients** never touch Unreal directly. They talk to the server via NNG sockets.
4. **Scenes are loaded by the client.** The simulator starts empty; the client sends JSONC config to construct the world.

### Checkpoint
Draw (on paper or in a diagram tool) the data flow from a Python `drone.move_by_velocity_async()` call to the physics engine and back to a `/actual_pose` topic. Label every process boundary and port.

---

## Module 1 — Environment Setup & First Flight (Headless)

**Goal**: Build SimLibs, launch the headless Runtime, and fly a drone with Python.

### Learning Objectives
- Build the C++ simulation libraries from source.
- Install the Python client in editable mode.
- Connect a client, load a scene, and execute a basic flight.

### Reading
| Resource | Why |
|---|---|
| `docs/development/dev_setup_linux.md` | Prerequisites, toolchain |
| `docs/development/use_source.md` | Build targets explained |
| `docs/client_setup.md` | Python environment setup |
| `AGENTS.md` | Build quirks, output paths, clang-13 workaround |

### Lab 1.1 — Build the Simulation Libraries
```bash
./setup_linux_dev_tools.sh          # one-time prerequisites
./build.sh simlibs_debug             # ~45 min first time, downloads deps
./build.sh test_simlibs_debug        # run C++ unit tests via ctest
```
Verify: `ls build/linux64/system/Debug/samples/projectairsim_runtime/projectairsim-runtime`

> On Ubuntu 24.04+ without `UE_ROOT`: symlink `clang-18` → `clang-13` (see `AGENTS.md`).

### Lab 1.2 — Install the Python Client
```bash
python -m venv airsim-venv && source airsim-venv/bin/activate
cd client/python/projectairsim
pip install -e ".[datacollection,tests]"
```

### Lab 1.3 — Hello Runtime
Terminal 1:
```bash
./build/linux64/system/Debug/samples/projectairsim_runtime/projectairsim-runtime
```
Terminal 2:
```bash
python client/python/example_user_scripts/projectairsim_runtime/projectairsim_runtime_demo.py
```
Study `projectairsim_runtime_demo.py` line by line. Identify: client connect, `World()` construction, `Drone()` wrapper, async move calls, topic subscription.

### Lab 1.4 — Read the Core Script
Open `client/python/example_user_scripts/hello_drone.py` and trace:
- `ProjectAirSimClient()` → `connect()`
- `World(client, "scene_basic_drone.jsonc", delay_after_load_sec=2)`
- `drone.enable_api_control()` / `drone.arm()` / `takeoff_async()`
- `client.subscribe(drone.sensors["DownCamera"]["scene_camera"], callback)`

### Checkpoint Project
Write `my_first_mission.py` that: connects to Runtime, loads `scene_basic_drone.jsonc`, takes off, flies a 10 m square at 2 m/s, lands, and prints the final `actual_pose`. Run it against the headless Runtime.

---

## Module 2 — The Configuration System Deep Dive

**Goal**: Master the JSONC scene/robot/environment-actor config schema that defines every simulation.

### Learning Objectives
- Author scene configs from scratch.
- Author robot configs with links, joints, actuators, sensors, and controllers.
- Validate configs with the schema tooling.

### Reading
| Resource | Why |
|---|---|
| `docs/config.md` | Config overview and file relationships |
| `docs/config_scene.md` | Scene: actors, clock, geo-point, environment, wind |
| `docs/config_robot.md` | Robot: links, joints, actuators, sensors, controller |
| `docs/multiple_robots.md` | Multi-vehicle scenes |
| `docs/modify_drone_physical.md` | Mass, inertia, rotor parameters |
| `docs/modify_drone_visual.md` | Mesh/visual configuration |
| `client/python/projectairsim/src/projectairsim/schema/*.jsonc` | The actual JSON schemas |

### Lab 2.1 — Dissect a Robot
Open `client/python/example_user_scripts/sim_config/robot_quadrotor_fastphysics.jsonc`. Annotate every section:
- `physics-type`
- `links[]` with `inertial`, `collision`, `visual`
- `joints[]` connecting props to frame
- `controller` block and `simple-flight-api-settings`
- `actuators[]` with rotor parameters and `parent-link`
- `sensors[]` with `type`, `enabled`, `capture-settings`

### Lab 2.2 — Dissect a Scene
Open `scene_basic_drone.jsonc` and `scene_drone_sensors.jsonc`. Compare `actors[]`, `clock`, `home-geo-point`, and `environment` blocks.

### Lab 2.3 — Validate Your Configs
```bash
python tools/ci/validate_configs.py path/to/your_scene.jsonc path/to/your_robot.jsonc
```
Intentionally break a config (wrong type, missing required field) and read the validation error.

### Lab 2.4 — Multi-Vehicle
Study `two_drones.py` and `hexarotor.py`. Build a scene with one quadrotor and one hexarotor spawned 5 m apart.

### Checkpoint Project
Create `robot_my_hexarotor.jsonc` with six rotors, custom mass (2.5 kg), an IMU, a GPS, and a barometer. Create `scene_my_hexarotor.jsonc` loading it. Validate both and fly it on the Runtime.

---

## Module 3 — Python Client API & Vehicle Control

**Goal**: Become fluent in the full Python API surface for control, sensing, and world interaction.

### Learning Objectives
- Use all move APIs (velocity, position, path, by-heading).
- Subscribe to topics and handle async callbacks correctly.
- Query and manipulate world state.
- Use the step/manual-clock APIs for deterministic simulation.

### Reading
| Resource | Why |
|---|---|
| `docs/api.md` | Full API reference |
| `client/python/projectairsim/docs/` | Sphinx API docs (`make html`) |
| `client/python/projectairsim/src/projectairsim/drone.py` | Drone class source |
| `client/python/projectairsim/src/projectairsim/world.py` | World class source |
| `client/python/projectairsim/src/projectairsim/client.py` | Client/RPC source |
| `docs/scene/sim_clock.md` | Clock modes |

### Labs — Work Through These Scripts in Order
| Script | Teaches |
|---|---|
| `move_apis.py` | Every move primitive and `wait_on_last_task` semantics |
| `sensors.py` | Subscribing to IMU, GPS, baro, magnetometer |
| `pubsub_reliability.py` | Topic reliability and message ordering |
| `clock_manual_step.py` | Deterministic stepping (`world.pause()`, `continue_for_sim_time()`) |
| `demo_engine_driven_clock.py` | Engine-driven clock mode |
| `geo_apis.py` | NED ↔ geodetic conversions |
| `config_object.py` | Programmatic config building |
| `spawn_runtime_objects.py` | Spawn/destroy objects at runtime |
| `list_resources.py` | Discover scene assets |
| `wind.py` | Environmental forces |
| `battery_simple.py`, `battery_energy_consumption.py` | Battery sensor models |
| `keyboard_control.py`, `xbox_rc.py` | Manual control input |
| `execute_missions.py`, `mission_with_validation.py` | Mission scripting and validation module |
| `debug_utils.py` | Debugging helpers |

### Lab 3.x — Async Patterns
The API is `asyncio`-based. Study how `move_task = await drone.move_by_velocity_async(...)` returns a task, then `await move_task` waits for completion. Experiment with running two drones concurrently using `asyncio.gather()`.

### Checkpoint Project
Build a **mission runner** that reads waypoints from a JSON file, flies the drone through them with position control, logs IMU/GPS at 10 Hz to CSV, and uses `mission_validation_module.py` patterns to assert the drone reached each waypoint within 0.5 m. Run it with manual-step clock for reproducibility.

---

## Module 4 — Unreal Engine Host & Rendering

**Goal**: Build and run the Unreal Blocks environment; understand the plugin architecture.

### Learning Objectives
- Install UE 5.2/5.7/5.8 and build the Blocks project.
- Understand how the plugin embeds SimLibs.
- Run headless (`-RenderOffScreen`) vs. windowed.
- Use command-line switches.

### Reading
| Resource | Why |
|---|---|
| `docs/development/dev_setup_linux.md` §5–6 | UE installed build (~200 GB, ~4 hr) |
| `docs/use_plugin.md` | Using the plugin in custom environments |
| `docs/command_line_switches.md` | `-RenderOffScreen`, `-nullrhi`, port switches |
| `docs/development/headless_cloud.md` | Headless debugging |
| `docs/sensors/camera_streaming.md` | Pixel streaming |
| `unreal/Blocks/Plugins/ProjectAirSim/Source/ProjectAirSim/Public/*.h` | Plugin public API |
| `unreal/Blocks/Plugins/ProjectAirSim/Source/ProjectAirSim/Private/UnrealSimLoader.cpp` | How SimLibs are loaded |

### Lab 4.1 — Build Blocks
```bash
export UE_ROOT=/path/to/UE_installed_build
./build.sh simlibs_debug          # now uses Unreal's toolchain → build/linux64/<UE-dirname>/
./build.sh blocks_debuggame       # builds plugin + Blocks + BlocksEditor
```

### Lab 4.2 — Run the Editor
Open `unreal/Blocks/Blocks.uproject` in UnrealEditor, press Play, then run `hello_drone.py`. Watch the drone spawn and camera windows appear.

### Lab 4.3 — Run Headless Game Mode
```bash
$UE_ROOT/Engine/Binaries/Linux/UnrealEditor unreal/Blocks/Blocks.uproject -game -RenderOffScreen
```
Run `camera_image_types.py` and confirm images still arrive without a window.

### Lab 4.4 — Explore the Plugin
Read these in order:
1. `ProjectAirSimGameMode.cpp` — entry point
2. `UnrealSimLoader.cpp` — SimLibs initialization, server start
3. `UnrealScene.cpp` — scene actor management
4. `Robot/UnrealRobot.cpp` + `UnrealRobotLink.cpp` — robot → actor mapping
5. `World/WorldSimApi.cpp` — world manipulation RPCs

### Lab 4.5 — Vehicle Blueprints
Read `docs/unreal_vehicle_blueprint_setup.md` and run `hello_unreal_vehicle_simpledrive.py`. Understand how a Chaos vehicle Blueprint is driven from the sim.

### Checkpoint Project
Package a standalone Blocks binary (`./build.sh package_blocks_development`), launch it with `run_sim_with_streaming.sh`, and view the simulation in a browser via Pixel Streaming.

---

## Module 5 — Sensors: Cameras, LiDAR, Radar, Segmentation

**Goal**: Configure and consume every rendered sensor type; understand their performance characteristics.

### Learning Objectives
- Configure camera capture settings (resolution, FOV, image types, post-processing).
- Use CPU LiDAR, GPU LiDAR, depth LiDAR, and Livox models.
- Configure radar detections/tracks.
- Use segmentation and bounding-box annotation.
- Inject sensor faults.

### Reading
| Resource | Why |
|---|---|
| `docs/sensors/camera_capture_settings.md` | All camera parameters |
| `docs/sensors/segmentation.md` | Semantic segmentation IDs |
| `docs/sensors/lidar.md` | LiDAR types and parameters |
| `docs/sensors/radar.md` | Radar model |
| `docs/sensors/battery.md` | Battery sensor |
| `docs/sensors/camera_post_processing_with_nn.md` | ONNX in-sim inference |
| `unreal/.../Private/Sensors/UnrealCamera.cpp` | Camera implementation |
| `unreal/.../Private/Sensors/GPULidar.cpp` + `LidarPointCloudCS.cpp` | Compute-shader LiDAR |

### Labs
| Script | Config | Teaches |
|---|---|---|
| `camera_image_types.py` | `scene_drone_sensors.jsonc` | RGB, depth, depth-planar, segmentation, surface normals |
| `camera_pose.py` | — | Moving cameras at runtime |
| `camera_faults.py` | — | Fault injection |
| `lidar_basic.py` | `scene_lidar_drone.jsonc` | CPU LiDAR point cloud |
| `lidar_basic_gpu.py` | `scene_lidar_drone_gpu.jsonc` | GPU LiDAR (much faster) |
| `depth_lidar.py` | `scene_lidar_depth.jsonc` | Depth-camera-derived LiDAR |
| `lidar_livox.py` | `scene_lidar_avia.jsonc`, `scene_lidar_mid70.jsonc` | Livox non-repetitive patterns |
| `static_sensor_actor_radar_tower.py` | `radar_tower.jsonc` | Radar on a static actor |
| `bbox_object_detection.py` | `scene_nonphysics_annotations_drone.jsonc` | 2D/3D bounding boxes |
| `computer_vision.py` | `scene_computer_vision.jsonc` | Non-physics camera rig |
| `onnx_ml_model.py` | `scene_onnx.jsonc` | In-sim ONNX inference |
| `object_material_manipulate.py` | — | Runtime texture/material swaps |

### Lab 5.x — Benchmark
Run `client/python/projectairsim/tests/test_camera_benchmarker.py` and `test_lidar_benchmarker.py` patterns. Measure FPS at 640×480 vs 1920×1080, and CPU vs GPU LiDAR at 100k vs 1M points/s.

### Checkpoint Project
Build a **sensor rig config** with: forward RGB+depth camera (1280×720, 90° FOV), downward segmentation camera, a 32-channel GPU LiDAR, and a radar. Write a script that records 30 seconds of synchronized data to disk (images as PNG, point clouds as NPY) with timestamps, and produces a timing report showing per-sensor latency.

---

## Module 6 — Physics Engines & Vehicle Types

**Goal**: Understand and select the right physics model; work with multirotors, fixed-wing, VTOL, and ground vehicles.

### Learning Objectives
- Compare Fast Physics, JSBSim, Simulink/MATLAB, Unreal (Chaos), and non-physics modes.
- Configure fixed-wing aircraft with JSBSim.
- Configure quadtiltrotor VTOL.
- Configure rovers and wheeled vehicles.

### Reading
| Resource | Why |
|---|---|
| `docs/physics/fast-physics.md` | Default multirotor physics |
| `docs/physics/jsbsim.md` | Fixed-wing flight dynamics |
| `docs/physics/matlab.md` | Simulink physics/controller integration |
| `docs/physics/no_physics.md` | Kinematic-only mode |
| `docs/wheeled_vehicle.md` | UGV support |
| `physics/include/*.hpp` | Physics interface headers |
| `physics/src/fast_physics.cpp` | Read the actual integrator |

### Labs
| Script | Teaches |
|---|---|
| `hello_drone.py` | Fast Physics baseline |
| `nonphysics_drone.py` | Kinematic mode for CV data capture |
| `jsbsim/cessna_310/*`, `jsbsim/x8_skywalker/*` | Fixed-wing with JSBSim |
| `quadtiltrotor_airtaxi_dfw.py` | VTOL transition |
| `config_quadtiltrotor_sf_params.py` | Tuning SimpleFlight gains |
| `hello_rover.py` | Fast Physics rover |
| `hello_wheeled_vehicle.py` | Native wheeled vehicle API |
| `hello_unreal_vehicle.py` | Chaos vehicle via Blueprint |
| `simulink_physics_quadrotor.py` | External physics via Simulink |

### Lab 6.x — Read the C++
Trace `physics/src/fast_physics.cpp`: find where rotor thrust is computed, drag applied, and the integration step performed. Compare to `physics/src/jsbsim_physics.cpp` to see how an external FDM is wrapped.

### Checkpoint Project
Configure a Skywalker X8 fixed-wing with JSBSim, write a script that takes off from a runway, climbs to 100 m, flies a 1 km racetrack pattern, and lands. Log airspeed, altitude, and pitch. Then repeat with a quadtiltrotor and compare transition behavior.

---

## Module 7 — Flight Controllers: SimpleFlight, PX4, ArduPilot

**Goal**: Integrate real autopilot firmware with the simulator in SITL and HITL.

### Learning Objectives
- Understand the controller abstraction (`vehicle_apis/`).
- Run PX4 SITL in lockstep with Project AirSim.
- Run ArduPilot SITL.
- Configure PX4 HITL over serial.
- Debug MAVLink connectivity.

### Reading
| Resource | Why |
|---|---|
| `docs/controllers/controllers.md` | Controller overview |
| `docs/controllers/simple_flight.md` | Built-in controller |
| `docs/controllers/px4/px4.md` | PX4 overview, version constraints |
| `docs/controllers/px4/px4_build.md` | Building PX4 v1.12.3 |
| `docs/controllers/px4/px4_sitl.md` | Full SITL walkthrough |
| `docs/controllers/px4/px4_lockstep.md` | Lockstep timing |
| `docs/controllers/px4/px4_multi_vehicle.md` | Multiple PX4 instances |
| `docs/controllers/px4/px4_hitl.md` | Hardware in the loop |
| `docs/controllers/ardupilot.md` | ArduPilot SITL |
| `mavlinkcom/include/MavLinkConnection.hpp` | MAVLink transport layer |
| `vehicle_apis/multirotor_api/` | Controller implementations |

### Lab 7.1 — PX4 SITL
```bash
# Terminal 1: PX4 (must be v1.12.3)
cd PX4-Autopilot && git checkout v1.12.3 && make px4_sitl none_iris
# Wait for: "Waiting for simulator to connect on TCP port 4560"

# Terminal 2: Simulator (Unreal or Runtime)

# Terminal 3:
python client/python/example_user_scripts/px4_quadrotor.py
```
Confirm in PX4 console: `EKF GPS checks passed`, `home: ...`. Then `px4_mission.py` for a MAVLink mission.

### Lab 7.2 — PX4 Parameters
Study the `parameters` block in `robot_quadrotor_px4_sitl.jsonc`. Explain why `NAV_RCL_ACT=0`, `NAV_DLL_ACT=0`, `COM_OBL_RC_ACT=1`, and why `LPE_LAT/LON` must match `home-geo-point`.

### Lab 7.3 — ArduPilot
Run `ardupilot/ardupilot_quadrotor.py` with the provided `.param` file.

### Lab 7.4 — Gimbal via MAVLink
Run `scene_px4_gimbal.jsonc` with `robot_quadrotor_px4_gimbal.jsonc`.

### Lab 7.5 — The Regression Test
Read `client/python/projectairsim/tests/px4_test_sitl.py`. Run it:
```bash
cd client/python/projectairsim/tests
pytest -m px4 --sim-host px4 px4_test_sitl.py
```

### Checkpoint Project
Run **two PX4 SITL instances** with two drones (`px4_multi_vehicle.md`), each on separate ports. Connect QGroundControl to both. Fly them in formation using the Python API and verify they appear in QGC with correct telemetry.

---

## Module 8 — ROS 2 Integration

**Goal**: Bridge Project AirSim into a ROS 2 graph and build ROS 2 nodes that consume sim data and command vehicles.

### Learning Objectives
- Build and run the C++ ROS 2 bridge (`projectairsim_ros2_cpp`).
- Understand topic/service/action mapping.
- Use sim time correctly.
- Visualize in RViz2.
- Write custom subscriber and controller nodes.
- Use the Python bridge (legacy) when needed.

### Reading
| Resource | Why |
|---|---|
| `docs/ros/ros2.md` | **Read in full.** Build, params, topics, services, actions, Fast DDS SHM profile |
| `docs/ros/ros.md` | Python bridge (ROS1/ROS2) |
| `ros/projectairsim_ros2_cpp/src/projectairsim_ros2_cpp_node.cpp` | The bridge node |
| `ros/projectairsim_ros2_cpp/include/projectairsim_ros2_cpp/ros2_conversion_utils.hpp` | Message conversions |
| `ros/projectairsim_ros2_cpp/msg/`, `srv/`, `action/` | Custom interfaces |
| `ros/projectairsim_ros2_cpp/test/*.cpp` | Contract tests |
| `ros/examples/build_map/`, `ros/examples/navigate_map/` | MoveIt/Octomap examples |
| `client/cpp/README.md`, `docs/cpp_client.md` | The C++ client the bridge uses |

### Lab 8.1 — Build & Run the Bridge
```bash
source /opt/ros/humble/setup.bash
cd ros && colcon build --packages-select projectairsim_ros2_cpp && source install/setup.bash
ros2 run projectairsim_ros2_cpp projectairsim_ros2_cpp_node --ros-args \
  -p scene_config:=scene_drone_sensors.jsonc \
  -p sim_config_path:=../client/python/example_user_scripts/sim_config
```
```bash
ros2 topic list -t
ros2 topic echo /ProjectAirsim/<scene>/robots/Drone1/actual_pose
ros2 topic hz /ProjectAirsim/<scene>/robots/Drone1/imu
```

### Lab 8.2 — Services & Actions
```bash
ros2 service call /projectairsim/Drone1/arm projectairsim_ros2_cpp/srv/Arm "{wait_on_last_task: true}"
ros2 service call /projectairsim/Drone1/takeoff projectairsim_ros2_cpp/srv/Takeoff "{wait_on_last_task: true}"
ros2 action send_goal /projectairsim/Drone1/move_on_path projectairsim_ros2_cpp/action/MoveOnPath "{...}"
```

### Lab 8.3 — RViz2
Launch RViz2 with `use_sim_time:=true`, set fixed frame to `map`, add TF, PoseStamped, Image, and PointCloud2 displays. Fly the drone via services and watch it move.

### Lab 8.4 — Custom Node
Write a ROS 2 Python node that subscribes to `/ProjectAirsim/.../lidar` (PointCloud2), computes the nearest obstacle distance, and publishes a `std_msgs/Float32`. Then write a second node that calls `move_to_position` service to back away if distance < 3 m.

### Lab 8.5 — 4K Images over Shared Memory
Follow the Fast DDS SHM section in `ros2.md`. Configure a 3840×2160 camera, enable the profile, and verify frame rate with `ros2 topic hz`.

### Lab 8.6 — Run the Contract Tests
```bash
cd ros && colcon test --packages-select projectairsim_ros2_cpp && colcon test-result --all --verbose
```
Read `ros2_bridge_surface_regression_test.cpp` to see what is guaranteed.

### Lab 8.7 — Nav2 / MoveIt Integration
Study `ros/examples/build_map/build_map.py` and `navigate_map.py`. Use `/projectairsim/create_voxel_grid` and `/projectairsim/occupancy_grid` to feed a planner.

### Checkpoint Project
Build a **ROS 2 autonomy stack**: bridge → custom perception node (detect landing pad from downward camera using OpenCV) → custom planner node (compute approach trajectory) → control node (calls bridge services). Launch everything from a single `launch.py`. Record a rosbag of the mission and replay it in RViz2.

---

## Module 9 — Advanced Simulation: Clocks, Weather, Environment Actors, GIS

**Goal**: Control time, environment, and world content for realistic and reproducible scenarios.

### Learning Objectives
- Use all clock modes for determinism and faster-than-real-time.
- Configure weather, time of day, wind.
- Place environment actors with trajectories.
- Load GIS scenes from glTF tiles.
- Script non-cooperative actors.

### Reading
| Resource | Why |
|---|---|
| `docs/scene/sim_clock.md` | Clock modes |
| `docs/development/scene/sim_clock_internal.md` | Clock internals |
| `docs/scene/weather_visual_effects.md` | Weather |
| `docs/gis_scenes.md` | GIS tile scenes |
| `docs/config_scene.md` §environment-actors | Env actor schema |
| `core_sim/include/core_sim/clock.hpp` | Clock implementation |
| `core_sim/include/core_sim/trajectory.hpp` | Trajectory interpolation |

### Labs
| Script | Teaches |
|---|---|
| `clock_manual_step.py` | Deterministic stepping |
| `demo_engine_driven_clock.py` | Engine-driven |
| `weather.py` | Rain, snow, fog, dust |
| `time_of_day.py` | Sun position |
| `light_objects.py` | Dynamic lights |
| `wind.py` | Wind fields |
| `env_actors_ned.py`, `env_actors_geo.py` | Scripted actors with trajectories |
| `non_cooperative_actor_demo.py` | Adversarial/non-cooperative actors |
| `hello_gis.py`, `gis_dfw.py` | GIS scenes |
| `airtaxi_dynamic_city_traj.py` | Complex city scenario |
| `hello_blackshark.py` | Blackshark.ai integration |
| `fault_injection_module.py` | Fault injection framework |

### Checkpoint Project
Build a **scenario generator**: a Python script that produces N randomized scene configs varying weather, time of day, wind, and env-actor trajectories, then runs each scenario with manual-step clock at 10× real-time, recording whether the drone completes its mission. Produce a results table.

---

## Module 10 — Autonomy, Data Collection & Machine Learning

**Goal**: Use the simulator as a data engine and RL environment.

### Learning Objectives
- Configure and run the data-collection pipeline.
- Apply domain randomization and augmentation.
- Use Gym environments for RL.
- Run pre-trained perception models.
- Use the testbench for coverage-driven scenario variation.

### Reading
| Resource | Why |
|---|---|
| `docs/autonomy/autonomy.md` | Overview |
| `docs/autonomy/setup.md` | Python deps (torch, etc.) |
| `docs/autonomy/gym/gym_envs.md` | RL environments |
| `docs/datacollection/*.md` | Config, trajectory, randomization, augmentation, aggregation, Azure |
| `client/python/projectairsim/src/projectairsim/datacollection/` | Pipeline source |
| `client/python/projectairsim/src/projectairsim/autonomy/` | Models, gym envs, serving |

### Labs
| Script | Teaches |
|---|---|
| `datacollection/basic_datacollection.py` | End-to-end collection |
| `datacollection/datacollection_trajectory_apis.py` | Trajectory generation |
| `datacollection/datacollection_augmentation_apis.py` | Augmentations |
| `datacollection/datacollection_validation_apis.py` | Dataset validation |
| `autonomy/landingpad_predictor_offboard.py` | Pre-trained perception |
| `autonomy/takeoff_landing_sync.py` | Perception-in-the-loop landing |
| `autonomy/cell_tower_inspection_demo.py` | Inspection application |
| `autonomy/uam_demo.py` | Urban air mobility |
| `testbench_*.py` | Coverage-driven scenario testbench |

### Checkpoint Project
Collect a 5,000-image dataset of landing pads under randomized weather/lighting/pose, train a small detector (or fine-tune the provided one), deploy it as a ROS 2 node, and demonstrate closed-loop autonomous landing in the sim.

---

## Module 11 — Extending the Simulator (C++ SimLibs)

**Goal**: Add new sensors, actuators, physics, or RPC services to the core.

### Learning Objectives
- Navigate the SimLibs architecture.
- Add a new sensor type end-to-end (core_sim → Unreal → client).
- Add a new RPC service method.
- Write gtest unit tests.
- Use sanitizers.

### Reading
| Resource | Why |
|---|---|
| `core_sim/include/core_sim/` | Core abstractions: actor, link, joint, sensors, actuators, scene, service |
| `core_sim/src/` | Implementations |
| `core_sim/test/` | gtest examples |
| `simserver/src/simserver.cpp` | RPC server, service registration |
| `core_sim/include/core_sim/message/` | Message definitions |
| `unreal/.../Private/Sensors/UnrealSensorFactory.h` | Sensor factory pattern |
| `client/python/projectairsim/src/projectairsim/` | Client-side mirror |
| `.clang-format` | Style |

### Lab 11.1 — Trace a Sensor
Follow the IMU from config → `core_sim/src/sensors/imu.cpp` → topic publishing → Python `sensors.py` callback. Document every file touched.

### Lab 11.2 — Trace an RPC
Follow `drone.move_to_position_async()` from Python → msgpack → `simserver` → `vehicle_apis/multirotor_api` → controller. Document every file.

### Lab 11.3 — Add a Service
Add a new RPC `GetBatteryHealth` that returns a struct. Register it in the service manager, add a Python client method, write a gtest, run `./build.sh test_simlibs_debug`.

### Lab 11.4 — Sanitizers
```bash
./build.sh simlibs_debug_asan
./build.sh simlibs_debug_tsan
```
Run unit tests under each and fix any findings.

### Lab 11.5 — The C++ Client
```bash
./build_cpp_client.sh debug --tests
```
Read `client/cpp/ProjectAirsimClientLib/` and `client/cpp/example_user_apps/HelloDrone/HelloDrone.cpp`. Compare the C++ and Python API surfaces.

### Checkpoint Project
Implement a **simulated ultrasonic range sensor** (cone-shaped, noisy, max 5 m) in SimLibs, expose it in the Unreal plugin using raycasts, add schema support, add a Python accessor, add a ROS 2 bridge conversion to `sensor_msgs/Range`, and write tests at every layer.

---

## Module 12 — Capstone Projects

Pick one (or more). Each should be a self-contained repo with README, configs, launch files, and a demo video.

### Capstone A — Full ROS 2 Autonomous Inspection Drone
- PX4 SITL + Project AirSim (Unreal) + ROS 2 bridge
- Nav2-style planner using occupancy grid service
- Camera-based anomaly detection on a cell tower or wind turbine
- Mission reporting with rosbag + validation XML output

### Capstone B — Multi-Vehicle Swarm Coordination
- 4+ drones, mixed SimpleFlight and PX4
- Formation control node in ROS 2
- Collision avoidance using LiDAR
- Deterministic replay using manual-step clock

### Capstone C — Sim-to-Real Perception Pipeline
- Domain-randomized data collection at scale
- Train detector, evaluate on held-out sim data
- Deploy as ONNX inside the sim (`onnx_ml_model.py` pattern) and as a ROS 2 node
- Measure sim latency vs. accuracy tradeoffs

### Capstone D — Ground + Air Heterogeneous Team
- Unreal Chaos UGV + quadrotor
- UGV maps with LiDAR → Octomap (`ros/examples/build_map`)
- Drone uses map for aerial path planning
- Coordinated via ROS 2 actions

### Capstone E — Simulator Contribution
- Identify a gap (new sensor, physics feature, bridge conversion)
- Implement across SimLibs, Unreal plugin, Python client, ROS 2 bridge
- Add tests at every layer, pass local CI checks (`tools/ci/`)
- Open a PR following `tools/ci/README.md` labeling rules

---

## Appendix A — Testing Discipline (Learn This Early)

```bash
# Offline (no simulator)
cd client/python/projectairsim/tests
python -m pytest --sim-host offline -v --timeout=120

# Against headless Runtime
python tools/ci/run_runtime_regressions.py --runtime build/linux64/system/Debug/samples/projectairsim_runtime/projectairsim-runtime

# Against Unreal (shared scene, one LoadScene per session)
python -m pytest --sim-host unreal -v --timeout=180

# C++ SimLibs
./build.sh test_simlibs_debug

# C++ client
./build_cpp_client.sh debug --tests

# ROS 2 bridge
cd ros && colcon test --packages-select projectairsim_ros2_cpp
```

**Every pytest test must declare exactly one host marker.** Bare `pytest` defaults to `--sim-host unreal`. See `client/python/projectairsim/tests/README.md`.

## Appendix B — Debugging Toolkit

| Problem | Tool |
|---|---|
| Client can't connect | `ss -tlnp \| grep -E '8989\|8990'` — is the server listening? |
| PX4 won't arm | PX4 console: `commander status`, `param show NAV_RCL_ACT`, wait for `home:` message |
| No topics in ROS 2 | `ros2 service call /projectairsim/get_topic_info ...` then check `scene_config` matches |
| Low FPS | `docs/system_specs.md` performance tips; `-RenderOffScreen`; reduce capture resolution |
| Determinism issues | Switch to manual-step clock; `docs/scene/sim_clock.md` |
| C++ crash | `./build.sh simlibs_debug_asan`; VS Code CodeLLDB launch configs |
| Config rejected | `python tools/ci/validate_configs.py <file>` |
| Unreal build fails | Check `UE_ROOT`, MSVC 14.37 (5.2) / 14.44 (5.7) on Windows, `./build.sh clean` |

## Appendix C — Progress Checklist

```
[ ] M0  Drew the end-to-end data flow diagram
[ ] M1  Built SimLibs, flew a square on headless Runtime
[ ] M2  Authored and validated custom hexarotor configs
[ ] M3  Built mission runner with CSV logging and validation
[ ] M4  Built Blocks, ran headless, packaged + pixel-streamed
[ ] M5  Built multi-sensor rig with synchronized recording
[ ] M6  Flew JSBSim fixed-wing racetrack + VTOL comparison
[ ] M7  Two PX4 SITL drones in formation with QGC
[ ] M8  ROS 2 perception → planner → control stack with rosbag
[ ] M9  Randomized scenario generator with results table
[ ] M10 Trained detector + closed-loop landing
[ ] M11 Ultrasonic sensor across all layers with tests
[ ] M12 Capstone complete with README + demo
```

---

*Course built from the Project AirSim repository at `iamaisim/ProjectAirSim`. All referenced files exist in this repo as of the authoring date.*
