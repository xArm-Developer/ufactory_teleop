# SpaceMouse Teleoperation

Control a UFACTORY xArm robot in Cartesian space with a supported 3Dconnexion SpaceMouse. The driver reads the device over HID and reconnects while the process is running.

## Supported Devices

The driver currently includes profiles for:

| Device | USB vendor:product ID |
| --- | --- |
| SpaceNavigator | `046D:C626` |
| SpaceMouse Compact | `256F:C635` |
| SpaceMouse Wireless | `256F:C62E` |
| SpaceMouse Pro Wireless | `256F:C632` |

Other devices are not guaranteed to work unless their HID report layout is added to the device map. The Pro Wireless profile exposes many buttons, but teleoperation uses only the first two mapped buttons for activation and quick actions.

## Requirements and HID Backend

- A UFACTORY robot reachable over the network, with its IP and startup pose configured.
- One of the supported SpaceMouse devices.
- Python packages listed in `requirements.txt`.

The backend is selected by platform:

- Linux and macOS always use HIDAPI (`hidapi`). Linux device permissions may need adjustment if the device cannot be opened; check the driver log for the failing device path/backend.
- Windows prefers `pywinusb` when installed, then falls back to HIDAPI. `pywinusb` is optional and is not listed in `requirements.txt`.
- On Windows, `SPACEMOUSE_BACKEND` can be set to `pywinusb`, `hidapi`, or `hid`. On Linux/macOS, HIDAPI is used regardless of this variable.

## Installation and Launch

From the repository root:

```bash
cd spacemouse_teleop
pip install -r requirements.txt
```

On Windows, optionally install `pywinusb` to use that backend:

```bash
pip install pywinusb
```

Edit `config/xarm6_spacemouse_teleop.yaml` for the target robot, then launch:

```bash
python uf_robot_spacemouse_teleop.py --config config/xarm6_spacemouse_teleop.yaml
```

The configuration path can also be supplied with the short option `-c`.

## Controls

| Input | Action |
| --- | --- |
| Hold the first and second mapped device buttons together for about 0.5 s | Activate or deactivate teleoperation |
| Hold the first mapped button alone | Level the tool orientation |
| Hold the second mapped button alone | Move the robot to its configured home position |
| Push/pull or tilt the cap | Command Cartesian translation and rotation on the six axes |

For SpaceNavigator, SpaceMouse Compact, and SpaceMouse Wireless, the first two mapped buttons are the left and right buttons. In the Pro Wireless profile, the first two mapped buttons correspond to Menu and Alt. Additional Pro Wireless buttons are not used by the teleoperation script.

The SpaceMouse axes command Cartesian targets in robot mode 7. Returning all axes to neutral stops the active motion. A device disconnect clears the active motion and deactivates control; reconnect the device and activate control again.

## Configuration

`RobotConfig` describes the robot connection and startup settings. Set `robot_ip` to the robot's address and review the startup joints, TCP pose, and gripper type for the target setup.

`TeleoperatorConfig` fields:

| Field | Meaning | Example |
| --- | --- | --- |
| `fps` | Cartesian command loop frequency | `30` |
| `leveling_speed` | Speed used by the leveling action | `45` |
| `homing_speed` | Speed used by the home action | `45` |
| `cartesian_speed` | Cartesian motion speed | `200` |
| `direction` | XY mapping orientation: `0`, `90`, `180`, or `270` degrees | `0` |
| `axes_deadzone` | Per-axis deadzone in `[x, y, z, roll, pitch, yaw]` order | `[0.15, 0.15, 0.10, 0.15, 0.15, 0.10]` |
| `max_distances` | Maximum pose offset in `[x, y, z, roll, pitch, yaw]` order; translation values use mm and rotation values use degrees | `[500, 500, 500, 60, 60, 60]` |

The example file uses a particular xArm6 startup pose. Confirm the robot address and setup-specific values before connecting.

## Safety

This software is not a safety-rated protective device. Keep the robot workspace clear, start at a safe speed and range, keep the robot's physical emergency stop accessible, and verify the configured home pose before using the home shortcut. Activation is an intentional software control toggle, not an emergency stop.
