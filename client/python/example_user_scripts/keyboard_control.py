"""
Copyright (C) 2025 IAMAI CONSULTING CORP
MIT License.

Keyboard-controlled drone example.

Uses the `inputs` package to read raw /dev/input/event* devices directly.
Unlike the `keyboard` package, `inputs` works with normal Linux group
permissions (membership in the "input" group) and does not require root.
"""

import argparse
import asyncio
import threading
import time
from typing import Dict, List

import inputs
import projectairsim
from projectairsim import Drone, World

# --- Keyboard State Tracking ---


def start_keyboard_listeners(key_state: Dict[str, bool]) -> List[threading.Thread]:
    """Spawn one daemon reader thread per detected keyboard device.

    Each thread blocks on raw evdev reads and updates `key_state` in place as
    keys are pressed/released. Multiple threads may be needed because some
    physical keyboards expose more than one /dev/input device node (e.g. a
    separate node for multimedia keys).

    Args:
        key_state: Shared dict this function will keep updated. Maps evdev
            key codes (e.g. "KEY_W") to whether they are currently held down.

    Returns:
        List[threading.Thread]: The started daemon reader threads.

    Raises:
        RuntimeError: If no keyboard device could be found.
    """
    if not inputs.devices.keyboards:
        raise RuntimeError(
            "No keyboard device found. Confirm your user is in the 'input' "
            "group (e.g. `sudo usermod -aG input $USER`, then log out and "
            "back in) and that a keyboard is attached."
        )

    threads = []
    for device in inputs.devices.keyboards:
        thread = threading.Thread(
            target=_read_keyboard_events,
            args=(device, key_state),
            daemon=True,
        )
        thread.start()
        threads.append(thread)
    return threads


def _read_keyboard_events(device, key_state: Dict[str, bool]) -> None:
    """Continuously read key press/release events from one device.

    Blocks on each read, so this must run in its own thread. Runs until the
    process exits (the thread is a daemon thread, so no explicit stop is
    needed).

    Each iteration yields a *list* of events (a raw evdev read can return
    several records at once, e.g. a key event plus its EV_SYN sync marker),
    not a single event.
    """
    for event_batch in device:
        for event in event_batch:
            if event.ev_type == "Key":
                # state: 0 = released, 1 = pressed, 2 = auto-repeat (held)
                key_state[event.code] = event.state != 0


def is_pressed(key_state: Dict[str, bool], code: str) -> bool:
    """Pure helper: check whether a given evdev key code is currently held."""
    return key_state.get(code, False)


# --- Drone Control Functions ---


async def takeoff(drone):
    """Arms the drone and takes off to a default altitude."""
    print("Arming the drone...")
    drone.arm()
    print("Taking off...")
    await drone.takeoff_async()
    time.sleep(1)


async def land(drone):
    """Lands the drone."""
    print("Landing...")
    await drone.land_async()
    print("Disarming the drone...")
    drone.disarm()


# --- Main Control Loop ---


async def run_keyboard_control(drone, key_state: Dict[str, bool]):
    """
    Controls the drone using keyboard inputs.

    Args:
        drone: The Drone object.
        key_state: Shared key-press state dict kept updated by the
            background listener threads (see start_keyboard_listeners).
    """

    # Enable API control
    drone.enable_api_control()

    # Takeoff
    await takeoff(drone)

    # Speed settings
    speed = 5  # m/s
    yaw_speed = 20  # degrees/s
    duration = 0.1  # seconds

    print("\n--- Keyboard Control ---")
    print("W/S: Pitch (Forward/Backward)")
    print("A/D: Roll (Left/Right)")
    print("Up/Down Arrows: Throttle (Altitude)")
    print("Left/Right Arrows: Yaw (Rotation)")
    print("L: Land")
    print("Q: Quit")
    print("--------------------")

    keep_running = True

    while keep_running:
        # Reset velocity components
        vx, vy, vz, yaw_rate = 0, 0, 0, 0

        # Pitch
        if is_pressed(key_state, "KEY_W"):
            vx = speed

        elif is_pressed(key_state, "KEY_S"):
            vx = -speed

        # Roll
        if is_pressed(key_state, "KEY_A"):
            vy = -speed

        elif is_pressed(key_state, "KEY_D"):
            vy = speed

        # Throttle
        if is_pressed(key_state, "KEY_UP"):
            vz = -speed  # Negative Z is up

        elif is_pressed(key_state, "KEY_DOWN"):
            vz = speed

        # Yaw
        if is_pressed(key_state, "KEY_LEFT"):
            yaw_rate = -yaw_speed

        elif is_pressed(key_state, "KEY_RIGHT"):
            yaw_rate = yaw_speed

        # Land and exit
        if is_pressed(key_state, "KEY_L"):
            await land(drone)
            keep_running = False

        # Quit
        if is_pressed(key_state, "KEY_Q"):
            keep_running = False

        # Move the drone in its body frame
        # vx, vy, vz are now interpreted as forward/backward, right/left, up/down relative to the drone
        if vx != 0 or vy != 0 or vz != 0:
            await drone.move_by_velocity_body_frame_async(vx, vy, vz, duration)
        if yaw_rate != 0:
            await drone.rotate_by_yaw_rate_async(yaw_rate, duration)
        await asyncio.sleep(0.01)


# --- Main Execution ---


async def main():
    parser = argparse.ArgumentParser(
        description="Example of using keyboard to control a drone in Project AirSim."
    )

    parser.add_argument(
        "--address",
        help=("the IP address of the host running Project AirSim"),
        type=str,
        default="127.0.0.1",
    )

    parser.add_argument(
        "--sceneconfigfile",
        help=(
            'the Project AirSim scene config file to load, defaults to "scene_basic_drone.jsonc"'
        ),
        type=str,
        default="scene_basic_drone.jsonc",
    )

    parser.add_argument(
        "--simconfigpath",
        help=(
            'the directory containing Project AirSim config files, defaults to "sim_config"'
        ),
        type=str,
        default="sim_config/",
    )

    parser.add_argument(
        "--topicsport",
        help=(
            "the TCP/IP port of Project AirSim's topic pub-sub client connection "
            '(see the Project AirSim command line switch "-topicsport")'
        ),
        type=int,
        default=8989,
    )

    parser.add_argument(
        "--servicesport",
        help=(
            "the TCP/IP port of Project AirSim's services client connection "
            '(see the Project AirSim command line switch "-servicessport")'
        ),
        type=int,
        default=8990,
    )

    args = parser.parse_args()
    client = projectairsim.ProjectAirSimClient(
        address=args.address,
        port_topics=args.topicsport,
        port_services=args.servicesport,
    )

    key_state: Dict[str, bool] = {}
    start_keyboard_listeners(key_state)

    drone = None
    try:
        client.connect()
        world = projectairsim.World(
            client=client,
            scene_config_name=args.sceneconfigfile,
            sim_config_path=args.simconfigpath,
        )
        drone = Drone(client, world, "Drone1")

        await run_keyboard_control(drone, key_state)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if drone:
            drone.disarm()
            drone.disable_api_control()
        client.disconnect()

        print("Cleaned up and disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
