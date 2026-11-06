#!/usr/bin/env python3
"""
ROS 2 Gamepad / Joystick Teleop Node for PX4 via MAVROS.

Subscribes to:
  - /joy   (sensor_msgs/msg/Joy)
  - /state (mavros_msgs/msg/State)

Publishes (at 30 Hz continuously):
  - /setpoint_raw/local  (mavros_msgs/msg/PositionTarget, FRAME_BODY_NED velocity + yaw_rate)
  - /manual_control/send (mavros_msgs/msg/ManualControl, when control_mode == "manual_control")

Calls MAVROS services on button presses (rising-edge triggered):
  - /cmd/arming (mavros_msgs/srv/CommandBool)
  - /set_mode   (mavros_msgs/srv/SetMode)
"""

from typing import List, Optional

from mavros_msgs.msg import ManualControl, PositionTarget, State
from mavros_msgs.srv import CommandBool, SetMode
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Joy


class Px4JoyTeleopNode(Node):
    """Translates sensor_msgs/msg/Joy from a Logitech/Xbox gamepad into MAVROS commands."""

    def __init__(self) -> None:
        super().__init__("px4_joy_teleop_node")

        # General parameters
        self.declare_parameter("control_mode", "offboard_velocity")  # "offboard_velocity" or "manual_control"
        self.declare_parameter("publish_rate_hz", 30.0)
        self.declare_parameter("deadzone", 0.08)
        self.declare_parameter("auto_detect_layout", True)

        # MAVROS topic/service names (matches `ros2 launch mavros px4.launch`)
        self.declare_parameter("joy_topic", "/joy")
        self.declare_parameter("state_topic", "/state")
        self.declare_parameter("setpoint_raw_topic", "/setpoint_raw/local")
        self.declare_parameter("manual_control_topic", "/manual_control/send")
        self.declare_parameter("arming_service", "/cmd/arming")
        self.declare_parameter("set_mode_service", "/set_mode")

        # Axis indices (Logitech F310 / F710 in XInput mode, Mode 2 RC layout)
        #   Left stick:  vertical = throttle (vz), horizontal = yaw_rate
        #   Right stick: vertical = pitch (vx forward), horizontal = roll (vy left)
        self.declare_parameter("axis_vx", 4)         # Right stick vertical (+1.0 = forward)
        self.declare_parameter("axis_vy", 3)         # Right stick horizontal (+1.0 = left)
        self.declare_parameter("axis_vz", 1)         # Left stick vertical (+1.0 = up)
        self.declare_parameter("axis_yaw_rate", 0)   # Left stick horizontal (+1.0 = yaw left / CCW)

        # Velocity / rate scales (in m/s and rad/s)
        self.declare_parameter("max_vx", 3.0)        # Max forward/backward speed (m/s)
        self.declare_parameter("max_vy", 3.0)        # Max left/right speed (m/s)
        self.declare_parameter("max_vz", 1.5)        # Max climb/descent speed (m/s)
        self.declare_parameter("max_yaw_rate", 1.0)  # Max yaw rate (rad/s)

        # Button indices (Logitech F310 / F710 in XInput mode)
        self.declare_parameter("btn_arm", 0)           # A: Arm
        self.declare_parameter("btn_disarm", 1)        # B: Disarm
        self.declare_parameter("btn_offboard", 2)      # X: OFFBOARD mode
        self.declare_parameter("btn_land", 3)          # Y: AUTO.LAND mode
        self.declare_parameter("btn_loiter", 4)        # LB: AUTO.LOITER (Hold position)
        self.declare_parameter("btn_takeoff", 5)       # RB: AUTO.TAKEOFF mode
        self.declare_parameter("btn_rtl", 6)           # Back: AUTO.RTL mode
        self.declare_parameter("btn_arm_offboard", 7)  # Start: Arm + switch to OFFBOARD

        self.control_mode: str = self.get_parameter("control_mode").value
        self.publish_rate_hz: float = float(self.get_parameter("publish_rate_hz").value)
        self.deadzone: float = float(self.get_parameter("deadzone").value)

        joy_topic: str = self.get_parameter("joy_topic").value
        state_topic: str = self.get_parameter("state_topic").value
        setpoint_raw_topic: str = self.get_parameter("setpoint_raw_topic").value
        manual_control_topic: str = self.get_parameter("manual_control_topic").value
        arming_service: str = self.get_parameter("arming_service").value
        set_mode_service: str = self.get_parameter("set_mode_service").value

        # Current state
        self.current_state = State()
        self.prev_buttons: List[int] = []
        self.cmd_vx: float = 0.0
        self.cmd_vy: float = 0.0
        self.cmd_vz: float = 0.0
        self.cmd_yaw_rate: float = 0.0
        self.raw_buttons_bitmask: int = 0
        self.pending_offboard_after_arm: bool = False

        # Subscribers
        self.state_sub = self.create_subscription(State, state_topic, self._on_state, 10)
        self.joy_sub = self.create_subscription(Joy, joy_topic, self._on_joy, 10)

        # Publishers (Reliable QoS is compatible with both SensorDataQoS and Reliable subscribers)
        pub_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.setpoint_raw_pub = self.create_publisher(PositionTarget, setpoint_raw_topic, pub_qos)
        self.manual_control_pub = self.create_publisher(ManualControl, manual_control_topic, 10)

        # Service clients
        self.arming_client = self.create_client(CommandBool, arming_service)
        self.set_mode_client = self.create_client(SetMode, set_mode_service)

        # Continuous setpoint timer (required >= 2 Hz by PX4 for OFFBOARD mode)
        self.timer = self.create_timer(1.0 / self.publish_rate_hz, self._on_timer)

        self.get_logger().info(
            f"PX4 Joy Teleop started (mode='{self.control_mode}', rate={self.publish_rate_hz:.0f} Hz)\n"
            f"  Sticks (Mode 2): Left=[Throttle, Yaw] | Right=[Pitch (Fwd/Back), Roll (Left/Right)]\n"
            f"  Buttons: A=Arm | B=Disarm | X=OFFBOARD | Y=LAND | LB=LOITER | RB=TAKEOFF | Back=RTL | Start=Arm+OFFBOARD"
        )

    def _apply_deadzone(self, value: float) -> float:
        if abs(value) < self.deadzone:
            return 0.0
        sign = 1.0 if value > 0.0 else -1.0
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)

    def _get_axis(self, axes: List[float], idx: int) -> float:
        if 0 <= idx < len(axes):
            return self._apply_deadzone(float(axes[idx]))
        return 0.0

    def _button_pressed(self, buttons: List[int], idx: int) -> bool:
        if 0 <= idx < len(buttons):
            curr = buttons[idx] == 1
            prev = (idx < len(self.prev_buttons)) and (self.prev_buttons[idx] == 1)
            return curr and not prev
        return False

    def _on_state(self, msg: State) -> None:
        self.current_state = msg

    def _on_joy(self, msg: Joy) -> None:
        auto_detect = bool(self.get_parameter("auto_detect_layout").value)
        if auto_detect and len(msg.axes) == 6:
            # 6-axis DirectInput / ShanWan PC/PS3/Android layout:
            #   axes[0]=LeftH, axes[1]=LeftV, axes[2]=RightH, axes[3]=RightV
            axis_vx = 3
            axis_vy = 2
            axis_vz = 1
            axis_yaw_rate = 0
        else:
            axis_vx = int(self.get_parameter("axis_vx").value)
            axis_vy = int(self.get_parameter("axis_vy").value)
            axis_vz = int(self.get_parameter("axis_vz").value)
            axis_yaw_rate = int(self.get_parameter("axis_yaw_rate").value)

        max_vx = float(self.get_parameter("max_vx").value)
        max_vy = float(self.get_parameter("max_vy").value)
        max_vz = float(self.get_parameter("max_vz").value)
        max_yaw_rate = float(self.get_parameter("max_yaw_rate").value)

        # Normalized stick values in [-1.0, 1.0]
        norm_vx = self._get_axis(msg.axes, axis_vx)
        norm_vy = self._get_axis(msg.axes, axis_vy)
        norm_vz = self._get_axis(msg.axes, axis_vz)
        norm_yaw = self._get_axis(msg.axes, axis_yaw_rate)

        self.cmd_vx = norm_vx * max_vx
        self.cmd_vy = norm_vy * max_vy
        self.cmd_vz = norm_vz * max_vz
        self.cmd_yaw_rate = norm_yaw * max_yaw_rate

        # Pack first 16 buttons into bitmask for ManualControl
        bitmask = 0
        for i, b in enumerate(msg.buttons[:16]):
            if b:
                bitmask |= 1 << i
        self.raw_buttons_bitmask = bitmask

        # Rising-edge button actions
        btn_arm = int(self.get_parameter("btn_arm").value)
        btn_disarm = int(self.get_parameter("btn_disarm").value)
        btn_offboard = int(self.get_parameter("btn_offboard").value)
        btn_land = int(self.get_parameter("btn_land").value)
        btn_loiter = int(self.get_parameter("btn_loiter").value)
        btn_takeoff = int(self.get_parameter("btn_takeoff").value)
        btn_rtl = int(self.get_parameter("btn_rtl").value)
        btn_arm_offboard = int(self.get_parameter("btn_arm_offboard").value)

        if self._button_pressed(msg.buttons, btn_arm):
            self.call_arm(True)
        if self._button_pressed(msg.buttons, btn_disarm):
            self.call_arm(False)
        if self._button_pressed(msg.buttons, btn_offboard):
            self.call_set_mode("OFFBOARD")
        if self._button_pressed(msg.buttons, btn_land):
            self.call_set_mode("AUTO.LAND")
        if self._button_pressed(msg.buttons, btn_loiter):
            self.call_set_mode("AUTO.LOITER")
        if self._button_pressed(msg.buttons, btn_takeoff):
            self.call_set_mode("AUTO.TAKEOFF")
        if self._button_pressed(msg.buttons, btn_rtl) or (
            auto_detect and len(msg.axes) == 6 and self._button_pressed(msg.buttons, 8)
        ):
            self.call_set_mode("AUTO.RTL")
        if self._button_pressed(msg.buttons, btn_arm_offboard) or (
            auto_detect and len(msg.axes) == 6 and self._button_pressed(msg.buttons, 9)
        ):
            self.call_set_mode("OFFBOARD")
            self.call_arm(True)

        self.prev_buttons = list(msg.buttons)

    def call_arm(self, value: bool) -> None:
        if not self.arming_client.service_is_ready():
            self.get_logger().warn("Arming service (/cmd/arming) is not available yet.")
            return
        req = CommandBool.Request()
        req.value = value
        action_str = "Arming" if value else "Disarming"
        self.get_logger().info(f"{action_str} drone via /cmd/arming...")
        future = self.arming_client.call_async(req)
        future.add_done_callback(
            lambda f: self.get_logger().info(
                f"{action_str} result: success={f.result().success}"
                if f.result() is not None
                else f"{action_str} call failed"
            )
        )

    def call_set_mode(self, mode: str) -> None:
        if not self.set_mode_client.service_is_ready():
            self.get_logger().warn("SetMode service (/set_mode) is not available yet.")
            return
        req = SetMode.Request()
        req.custom_mode = mode
        self.get_logger().info(f"Requesting flight mode '{mode}' via /set_mode...")
        future = self.set_mode_client.call_async(req)
        future.add_done_callback(
            lambda f: self.get_logger().info(
                f"SetMode '{mode}' result: mode_sent={f.result().mode_sent}"
                if f.result() is not None
                else f"SetMode '{mode}' call failed"
            )
        )

    def _on_timer(self) -> None:
        now = self.get_clock().now().to_msg()
        self.control_mode = str(self.get_parameter("control_mode").value)

        if self.control_mode == "manual_control":
            max_vx = max(float(self.get_parameter("max_vx").value), 1e-3)
            max_vy = max(float(self.get_parameter("max_vy").value), 1e-3)
            max_vz = max(float(self.get_parameter("max_vz").value), 1e-3)
            max_yaw_rate = max(float(self.get_parameter("max_yaw_rate").value), 1e-3)

            msg = ManualControl()
            msg.header.stamp = now
            msg.x = float(self.cmd_vx / max_vx)          # Pitch [-1..1] (+forward)
            msg.y = float(-self.cmd_vy / max_vy)         # Roll  [-1..1] (+right in MAVLink)
            msg.z = float(0.5 + 0.5 * (self.cmd_vz / max_vz))  # Throttle [0..1] (0.5 = hover)
            msg.r = float(-self.cmd_yaw_rate / max_yaw_rate)   # Yaw   [-1..1] (+clockwise in MAVLink)
            msg.buttons = int(self.raw_buttons_bitmask)
            self.manual_control_pub.publish(msg)
        else:
            # Default: OFFBOARD body-frame velocity control via /setpoint_raw/local
            # MAVROS converts PositionTarget.FRAME_BODY_NED from ROS base_link FLU
            # (+x = Forward, +y = Left, +z = Up, +yaw_rate = CCW/Left) to PX4 FRD.
            target = PositionTarget()
            target.header.stamp = now
            target.header.frame_id = "base_link"
            target.coordinate_frame = PositionTarget.FRAME_BODY_NED
            target.type_mask = (
                PositionTarget.IGNORE_PX
                | PositionTarget.IGNORE_PY
                | PositionTarget.IGNORE_PZ
                | PositionTarget.IGNORE_AFX
                | PositionTarget.IGNORE_AFY
                | PositionTarget.IGNORE_AFZ
                | PositionTarget.IGNORE_YAW
            )
            target.velocity.x = float(self.cmd_vx)
            target.velocity.y = float(self.cmd_vy)
            target.velocity.z = float(self.cmd_vz)
            target.yaw_rate = float(self.cmd_yaw_rate)
            self.setpoint_raw_pub.publish(target)


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = Px4JoyTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
