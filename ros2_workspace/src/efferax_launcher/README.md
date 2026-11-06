# `efferax_launcher` — Master Bringup for Efferax Autonomy Stack

Launches the complete ROS 2 autonomy and simulation stack in a single command:

1. **`projectairsim_ros2_cpp_node`** (`use_sim_bridge:=true`): Loads `scene_px4_sitl.jsonc` into Project AirSim (Unreal Blocks) and bridges Cameras, 3D GPU LiDAR, `/tf`, and `/clock`.
2. **MAVROS (`px4.launch`)** (`use_mavros:=true`): Bridges PX4 (`fcu_url:=udp://:14550@127.0.0.1:18570` in SITL, or serial on a real drone).
3. **Gamepad Teleop (`px4_joy_teleop`)** (`use_joy:=true`): Starts `joy_node` + `px4_joy_teleop_node` for Logitech/Xbox gamepad control over MAVROS.
4. **RViz2 (`rviz2`)** (`use_rviz:=true`): Opens RViz2 pre-configured with `px4_drone.rviz` (`Best Effort` QoS for Camera and LiDAR topics).

## Usage

Inside the `projectairsim-ros2-mavros` container:

```bash
# Launch everything (Sim Bridge + MAVROS + Gamepad Teleop + RViz2)
make autonomy
# or directly:
ros2 launch efferax_launcher efferax.launch.py

# Launch on real PX4 hardware (no simulator bridge, headless without RViz2):
ros2 launch efferax_launcher efferax.launch.py \
  use_sim_bridge:=false \
  use_rviz:=false \
  fcu_url:=/dev/ttyACM0:57600
```
