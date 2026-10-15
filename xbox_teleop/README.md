# Xbox Controller Teleoperation

Control a UFACTORY xArm robot in Cartesian space with an Xbox-compatible gamepad. The controller must be connected before or while the teleoperation process is running. Robot motion is disabled until control is activated.

## Requirements

- A UFACTORY robot reachable over the network, with its IP and startup pose configured.
- An Xbox-compatible gamepad recognized by the operating system.
- Python packages listed in `requirements.txt`.
- On Linux, the driver uses `evdev` when it is installed; otherwise it reads gamepads through `inputs`. Make sure the user running the program has permission to access the controller.

## Installation and Launch

From the repository root:

```bash
cd xbox_teleop
pip install -r requirements.txt
```

Edit `config/xarm6_xbox_teleop.yaml` for the target robot, then launch:

```bash
python uf_robot_xbox_teleop.py --config config/xarm6_xbox_teleop.yaml
```

The configuration path can also be supplied with the short option `-c`.

## Controls

| Input | Action |
| --- | --- |
| Hold `START` + `SELECT` for about 0.5 s | Activate or deactivate teleoperation |
| Hold `START` alone | Level the tool orientation |
| Hold `SELECT` alone | Move the robot to its configured home position |
| Briefly press and release `START` | Toggle the default Z/Yaw direction |
| D-pad up / down | Set Z/Yaw motion direction positive / negative while pressed |
| Left stick (`X`, `Y` axes) | Selects the corresponding X/Y translation input when moved |
| Right stick (`RX`, `RY` axes) | Controls roll/pitch when the corresponding rotational axis is enabled |
| Triggers (`Z`, `RZ` axes) | Control Z translation and yaw |
| Face button `X` or `Y` | Enable the corresponding X/Y translation axis and suppress roll/pitch input |
| Face button `A` or `B` | Enable the corresponding roll/pitch axis and suppress X/Y translation input |

With no face-axis selector held, the controller can command the available translation and rotation axes together. `direction` rotates the XY/roll/pitch mapping to match the operator's orientation. D-pad left/right do not alter the Z/Yaw sign.

Motion is sent as Cartesian targets in robot mode 7. Returning all axes to neutral stops the active motion. A controller disconnect also clears the active motion and deactivates control; reconnect the device and activate control again.

## Configuration

`RobotConfig` describes the robot connection and startup settings. At minimum, set `robot_ip` to the robot's address. Review `start_joints`, `start_tcp_pose`, and `gripper_type` for the setup before running.

`TeleoperatorConfig` fields:

| Field | Meaning | Example |
| --- | --- | --- |
| `fps` | Cartesian command loop frequency | `30` |
| `leveling_speed` | Speed used by the leveling action | `45` |
| `homing_speed` | Speed used by the home action | `45` |
| `cartesian_speed` | Cartesian motion speed | `200` |
| `direction` | XY mapping orientation: `0`, `90`, `180`, or `270` degrees | `0` |
| `axes_deadzone` | Per-axis deadzone in `[X, Y, Z, RX, RY, RZ]` order | `[0.15, 0.15, 0.1, 0.2, 0.2, 0.1]` |
| `max_distances` | Maximum pose offset in `[X, Y, Z, roll, pitch, yaw]` order; translation values use mm and rotation values use degrees | `[500, 500, 500, 60, 60, 60]` |

The example file uses conservative starting pose values for an xArm6 and is not universal. Confirm the robot address and setup-specific values before connecting.

## Safety

This software is not a safety-rated protective device. Keep the robot workspace clear, start at a safe speed and range, keep the robot's physical emergency stop accessible, and verify the configured home pose before using the home shortcut. Activation is an intentional software control toggle, not an emergency stop.
