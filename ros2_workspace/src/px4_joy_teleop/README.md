# `px4_joy_teleop` — Logitech / Xbox Gamepad Teleoperation for PX4 via MAVROS

Controls a PX4 drone (in Project AirSim or on real hardware) using a standard Linux gamepad (Logitech F310/F710, Xbox controller) strictly through **MAVROS** topics and services.

## Features

1. **Continuous 30 Hz Body-Frame Velocity Control (`control_mode: "offboard_velocity"`)**:
   - Publishes `mavros_msgs/msg/PositionTarget` (`FRAME_BODY_NED` / FLU body frame) to `/setpoint_raw/local` at 30 Hz so PX4 can enter and remain in `OFFBOARD` mode without timing out.
   - Centering the sticks sends zero velocity (`vx=0, vy=0, vz=0, yaw_rate=0`), causing PX4 to hold position and altitude smoothly.
2. **Native MAVLink Manual Control (`control_mode: "manual_control"`)**:
   - Publishes `mavros_msgs/msg/ManualControl` to `/manual_control/send` for flying in `POSCTL`, `ALTCTL`, or `STABILIZED` modes.
3. **Gamepad Button Bindings (Logitech F310/F710 in XInput Mode)**:
   - **`Start`**: Arm + Switch to `OFFBOARD` mode
   - **`A`**: Arm (`/cmd/arming` `true`)
   - **`B`**: Disarm (`/cmd/arming` `false`)
   - **`X`**: Switch to `OFFBOARD` mode (`/set_mode`)
   - **`Y`**: Land (`AUTO.LAND`)
   - **`RB`**: Takeoff (`AUTO.TAKEOFF`)
   - **`LB`**: Hold Position (`AUTO.LOITER`)
   - **`Back`**: Return to Launch (`AUTO.RTL`)

## Usage

Inside the `projectairsim-ros2-mavros` container:

```bash
# Build the package
make ros2-build PKG=px4_joy_teleop

# Launch joy_node + px4_joy_teleop_node
make joy-teleop
# Or directly via ros2 launch:
ros2 launch px4_joy_teleop joy_teleop.launch.py
```
