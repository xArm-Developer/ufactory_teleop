# uf_teleop_core

The shared, installable core library for all five teleoperation solutions. Each solution's own script handles only the loop of "read input → compute mapping → send action"; everything that talks to hardware lives here: the xArm wrapper and the drivers for the input devices, plus the unified teleop/robot device interfaces.

## Installation

From the repository root:

```bash
pip install -e .                          # core only (numpy, PyYAML)
pip install -e ".[pika]"                  # + xArm SDK + Pika serial deps (Pika SDK below)
pip install -e ".[umi]"                   # + xArm SDK + UMI camera deps (Vive SDK below)
pip install -e ".[gello]"                 # + Gello (Dynamixel) SDK
pip install -e ".[xbox]"                  # + Xbox-compatible gamepad
pip install -e ".[spacemouse]"            # + 3Dconnexion SpaceMouse
pip install -e ".[robot]"                 # + xArm Python SDK
pip install -e ".[vive]"                  # + full pysurvive/agx-pypika SDK (heavy)
pip install -e ".[dev]"                   # + pytest
pip install -e ".[all]"                   # everything above (excludes [vive])
```

System dependencies (Vive/Lighthouse via `pysurvive`, XVSDK deb, udev rules) are still installed per solution as described in the root README.

`pysurvive` and `agx-pypika` are installed separately with `--no-deps`, because their metadata pulls GUI/camera-only dependencies (`gooey`, `wxpython`, `pyrealsense2`) that the teleoperation path does not use:

```bash
pip install pysurvive agx-pypika --no-deps
```

For a declarative full SDK install (including Pika camera/GUI tools), use `pip install -e ".[pika,vive]"`. A normal install pulls the GUI/camera dependencies above; `--no-deps` cannot be combined with extras because it suppresses extra requirements too.

## Directory Structure

```
src/uf_teleop_core/
├── transformations.py          # Transformations: pose math utilities
├── devices/
│   ├── pika/
│   │   └── pika_device.py      # PikaDevice: Pika Sense / Pika Gripper serial driver
│   ├── umi/
│   │   ├── xvlib/              # XVLib: ctypes wrapper around libxvlib.so (+ bundled .so fallbacks)
│   │   └── vive_tracker/       # ViveTracker: HTC Vive Tracker driver built on pysurvive
│   ├── xbox/
│   │   └── xbox_device.py      # XBoxDevice: Xbox-compatible gamepad driver
│   ├── spacemouse/
│   │   └── space_device.py     # SpaceDevice: 3Dconnexion SpaceMouse driver
│   └── gello/
│       └── gello_device.py     # GelloDevice: Dynamixel + GelloAgent wrapper and calibration
├── teleop/
│   ├── base.py                 # TeleopData / TeleopDevice: teleop device interface
│   ├── mapping.py              # CartesianTeleopMapper: teleop pose -> robot target pose
│   ├── pika_teleop_device.py   # PikaTeleopDevice
│   ├── umi_teleop_device.py    # UmiTeleopDevice
│   ├── gello_teleop_device.py  # GelloTeleopDevice
│   ├── xbox_teleop_device.py   # XboxTeleopDevice (delta)
│   └── spacemouse_teleop_device.py # SpacemouseTeleopDevice (delta)
└── robot/
    ├── base.py                 # RobotDevice / RobotState: robot device interface
    └── uf_robot.py             # UFRobot: xArm connection, motion, gripper control
```

Import from the subpackages explicitly, for example `from uf_teleop_core.robot import UFRobot` or `from uf_teleop_core.devices.pika import PikaDevice`.

## Modules Used by Each Solution

| Teleoperation Solution | Imported from uf_teleop_core |
| --- | --- |
| [pika_teleop](../../pika_teleop/README.md) | `teleop.PikaTeleopDevice`, `teleop.CartesianTeleopMapper`, `robot.UFRobot` |
| [umi_teleop](../../umi_teleop/README.md) | `teleop.UmiTeleopDevice`, `teleop.CartesianTeleopMapper`, `robot.UFRobot` |
| [gello_teleop](../../gello_teleop/README.md) | `teleop.GelloTeleopDevice`, `robot.UFRobot` |
| [xbox_teleop](../../xbox_teleop/README.md) | `teleop.XboxTeleopDevice`, `robot.UFRobot` |
| [spacemouse_teleop](../../spacemouse_teleop/README.md) | `teleop.SpacemouseTeleopDevice`, `robot.UFRobot` |

## robot/ — xArm Wrapper

`from uf_teleop_core.robot import UFRobotConfig, UFRobot`

### UFRobotConfig

| Field | Description |
| --- | --- |
| `robot_ip` | xArm controller IP address. |
| `robot_mode` | Motion mode. `1` servo Cartesian, `6` joint control, `7` (default) online trajectory planning. |
| `robot_speed` / `robot_acc` | Motion speed and acceleration. |
| `gripper_type` | Gripper type; see `GripperType`. |
| `gripper_port` | Gripper serial port, used only by the Pika Gripper (`10`). |
| `gripper_speed` / `gripper_force` | `-1` uses the per-gripper default. |
| `start_joints` | Joint angles the arm moves to at startup, in radians. |
| `start_tcp_pose` | Optional. TCP pose `[x, y, z, roll, pitch, yaw]` to move to after `start_joints`. |

`GripperType` values: `NoGripper=0`, `xArmGripper=1`, `xArmGripperG2=2`, `BioGripperG2=3`, `PikaGripper=10`, `RobotiqGripper=11`.

### UFRobot

`UFRobot(config)` — on construction it connects to the controller, enables the motors, clears errors, and moves to `start_joints`. **Instantiating it moves the robot**, so confirm the workspace first.

- `send_action(action)` — the common dispatch interface used by every solution, split by `robot_mode`:
  - `robot_mode: 6`: `action[:axis_count]` are joint angles (radians), `action[axis_count]` is the normalized gripper value (0 open → 1 closed).
  - `robot_mode: 7` and others: `action[:6]` is `[x, y, z, rx, ry, rz]`, `action[6]` is the normalized gripper value.
  - The gripper is driven over TDK Modbus (xArm Gripper G1/G2, BIO Gripper G2, Robotiq) or serial (Pika Gripper), depending on type.
  - Returns the controller error code; callers should check it in their loop and exit on a non-zero value.
- `get_position(is_axis_angle=False)` — read the current pose (xyzrpy by default, or axis-angle).
- `get_state()` — read a `RobotState` snapshot: `tcp_pose` (xyzrpy, mm/rad), `joints` (rad), `gripper_norm` (last commanded), `error_code`.
- `robot_init(enable=True, init_gripper_pose=False)` — reset mode and state, optionally initializing the gripper.
- `close()` — disconnect the arm (and a Pika gripper, if used).
- `action_space` / `connected` — `RobotActionSpace.CARTESIAN` or `JOINT`, and the connection state.

`UFRobot` implements the `RobotDevice` interface in `robot/base.py` (`connect`, `close`, `get_state`, `send_action`, `action_space`), so any other robot backend can be dropped in. `RobotState` and `RobotActionSpace` are exported from `uf_teleop_core.robot`.

## teleop/ — Teleop Device Layer

`from uf_teleop_core.teleop import TeleopData, TeleopDevice, CartesianTeleopMapper`

A teleop device only reads input; it never touches the robot. `get_data()` returns the latest `TeleopData` frame, or `None` when no sample is available:

| Field | Description |
| --- | --- |
| `timestamp` | monotonic seconds. |
| `space` | `cartesian`, `cartesian_delta` or `joint`. |
| `position` | `[x, y, z]` in meters, device frame. |
| `quaternion` | attitude quaternion `[x, y, z, w]` (xyzw). |
| `joints` | joint angles in radians (Gello). |
| `gripper` | normalized `0` open → `1` closed; ready for `UFRobot.send_action`. |
| `buttons` | device states, e.g. Pika `{"command": 0/1}`, Xbox `{"START": 0/1, ...}`. |
| `delta` | `[dx, dy, dz, drx, dry, drz]` in mm/deg (rpy increments) for incremental devices. |
| `axes` | raw axis values for incremental devices (zero-input checks and data collection). |

Devices are independent of the robot and can be used standalone:

```python
from uf_teleop_core.teleop import PikaTeleopDevice

with PikaTeleopDevice(use_gripper=True) as device:
    data = device.get_data()
    if data is not None and data.valid:
        print(data.position, data.quaternion, data.gripper, data.buttons)
```

- `PikaTeleopDevice(pika_sense_port=None, vive_tracker_id=None, use_gripper=True, gripper_deadband=2.0)` — wraps `PikaDevice`; also exposes `get_command_state()`.
- `UmiTeleopDevice(serial_number, use_gripper=True, use_vive_tracker=False, vive_tracker_id='WM0')` — wraps `XVLib` (and `ViveTracker` when configured).
- `GelloTeleopDevice(port=None, joint_ids=(1,...,7), joint_signs=(1,...,1), start_joints=..., gripper_id=8, torque_joint_ids=None)` — uses `GelloDevice` for calibration and `GelloAgent`.
- `XboxTeleopDevice(axes_deadzone=..., max_distances=..., direction=0)` — wraps `XBoxDevice`; `get_data()` returns `CARTESIAN_DELTA` frames. `dz` / `drz` sign (D-pad / reversal toggle) is left to the caller.
- `SpacemouseTeleopDevice(axes_deadzone=..., max_distances=..., direction=0)` — wraps `SpaceDevice`; returns `CARTESIAN_DELTA` frames with `buttons` `LEFT` / `RIGHT`.

All devices implement `TeleopDevice` (`connect`, `close`, `get_data`) and support `with` usage. The underlying SDK objects remain accessible (`pika_sense`, `xvlib`, `tracker`, `gello_agent`) for raw data and camera streams. The Xbox / SpaceMouse entries keep their activation, leveling, homing and mode-switching state machines in the solution scripts: those are controller behaviors, not device readings.

`CartesianTeleopMapper(tracker_to_robot_eef, robot_base_pose=None, is_axis_angle=True)` maps cartesian `TeleopData` to a robot target pose `[x, y, z, rx, ry, rz]` (mm/rad) using relative motion: target = initial robot pose × inv(initial teleop pose) × current teleop pose. Call `reset(data, robot_tcp_pose)` when teleoperation starts (omit the pose when `robot_base_pose` is configured), then `map(data)` each frame. It reuses `Transformations.tracker_pose_to_robot_matrix()` / `tracker_robot_matrix_to_robot_pose()`.

For recording data without a robot, see [`scripts/collect_data.py`](../../scripts/collect_data.py); to replay recorded teleop frames on a robot, see [`scripts/replay_data.py`](../../scripts/replay_data.py).

## devices/pika/ — Pika Sense and Pika Gripper

`from uf_teleop_core.devices.pika import PikaDevice`

- `get_serial_ports(vidpid='1a86:7522')` — enumerate candidate serial ports by VID:PID.
- `check_pika_device(port)` — probe which device is on a port. Returns `-1` port cannot be opened, `0` not a Pika device, `1` Pika Sense, `2` Pika Gripper.
- `PikaDevice(dev_type=1, pika_sense_port=None, pika_gripper_port=None)` — `dev_type` is `1` for Sense only, `2` for Gripper only, `3` for both. Ports left unset are discovered by scanning and probing.
- The `pika_sense` / `pika_gripper` properties connect only on first access. Handles for the same port are reused through the class-level `PIKA_DEVICE_MAP`, so `UFRobot`'s Pika gripper and a teleoperation script can share one Sense instance.

Requires `agx-pypika` (which provides the `pika.sense` / `pika.gripper` modules), imported lazily inside the properties.

## devices/umi/ — FastUMI and Vive Tracker

`from uf_teleop_core.devices.umi import XVLib, Transformations` / `from uf_teleop_core.devices.umi import ViveTracker`

### xvlib/

`XVLib(serial_number, init_slam=False, init_clamp_stream=False, init_color_camera=False, init_fisheye_cameras=False)`

A ctypes wrapper around `libxvlib.so` that enumerates devices and initializes the data streams on demand. The calls teleoperation uses most:

- `xv_get_devices()` — enumerate connected FastUMI devices.
- `xv_get_slam_pose()` / `xv_get_slam_data()` — read the built-in SLAM pose.
- `xv_get_clamp_stream_data()` — read gripper open/close data.
- `xv_get_color_camera_data()` / `xv_get_fisheye_cameras_data()` — read camera frames as numpy arrays (requires `opencv-python`).

Loading order is: check the system XVSDK → preload `libtbb.so.2` → load `libopencv_*.so` → load `libxvlib.so`. These `.so` files are bundled with the package as a fallback; the bundled `libopencv_core.so.4.2` depends on the old TBB ABI, which is incompatible with the oneAPI TBB (`libtbb.so.12`) shipped in Ubuntu 22.04+, so the code preloads `libtbb.so.2` explicitly. If the XVSDK is not installed system-wide, it raises with the install command. Note that a wheel containing these `.so` files must be built as a Linux x86_64 platform wheel.

### vive_tracker/

- `ViveTracker(config_path=None, lh_config=None, args=None)` — a singleton (`SingletonMeta`) that collects poses on a background thread. `get_pose(device_name=None)` returns a pose, `get_raw_pose()` the raw pose, `get_tracked_device_names()` lists tracked devices, and `stop()` / `close()` release resources.
- `Transformations` — a static utility class: conversions between quaternions, rotation matrices, RPY, and axis-angle, plus `tracker_pose_to_robot_matrix()` / `tracker_robot_matrix_to_robot_pose()` for mapping tracker poses to robot poses. It now lives in `uf_teleop_core.transformations` and is re-exported here for compatibility.

## devices/xbox/ — Xbox-Compatible Gamepad

`from uf_teleop_core.devices.xbox import XBoxDevice`

- `XBoxDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.2, 0.2, 0.1], logger=None)` — a `threading.Thread` subclass with a daemon thread reading gamepad input continuously.
- Prefers `evdev` on Linux when installed, falling back to the `inputs` package otherwise.
- `connected` reports the connection state; `state` exposes sticks, triggers, buttons, and the D-pad; `set_axes_deadzone()` adjusts deadzones at runtime.

## devices/spacemouse/ — 3Dconnexion SpaceMouse

`from uf_teleop_core.devices.spacemouse import SpaceDevice`

- `SpaceDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.15, 0.15, 0.1], logger=None)` — likewise a background thread.
- HID backend: non-Windows platforms always use HIDAPI; on Windows, the `SPACEMOUSE_BACKEND` environment variable selects `hidapi`, `hid`, or `pywinusb`, defaulting to `pywinusb` with a HIDAPI fallback.
- `list_space_devices()` lists available devices; `connected`, `product_name`, `vendor_name`, `vendor_id`, and `product_id` describe the device; `state` exposes the six axes and buttons; `set_led(state)` controls the indicator LED; `register_state_changed_callback(cb)` registers a state callback.

## devices/gello/ — Gello Leader Arm

`from uf_teleop_core.devices.gello import GelloDevice`

- `GelloDevice(port=None, joint_ids=..., joint_signs=..., start_joints=..., gripper_id=8, torque_joint_ids=None)` — lazily imports the `gello` package in `connect()`.
- `connect()` reads the current leader-arm joints, computes the zero offsets, optionally enables torque mode, and creates the `GelloAgent`.
- `get_action()` returns `[joints..., gripper]` (or joints only when `gripper_id < 0`), `action_dim` and `gripper_id` are exposed, and `close()` releases the agent reference.

## Dependencies

| Module | Dependency | Notes |
| --- | --- | --- |
| `robot/` | `xarm-python-sdk` | Shared by every solution. |
| `devices/pika/` | `agx-pypika`, `pyserial` | `agx-pypika` provides the `pika` module; install it with `--no-deps` to skip its GUI/camera extras. |
| `devices/umi/xvlib/` | system XVSDK (`libxvsdk.so`), `opencv-python` | The deb install command is printed when the XVSDK is missing; camera frames need OpenCV. |
| `devices/umi/vive_tracker/` | `pysurvive` | Only needed when an HTC Vive Tracker is used; install with `--no-deps` to skip `gooey`. |
| `devices/xbox/` | `inputs`, optionally `evdev` on Linux | `evdev` is preferred when present. |
| `devices/spacemouse/` | `hidapi` (import name `hid`), optionally `pywinusb` on Windows | See the backend selection rules above. |
| `devices/gello/` | `gello` (pinned GitHub archive), `dynamixel-sdk` (PyPI) | Installed by the `gello` extra. The archive URL avoids pip fetching gello's unused git submodules. |

These are declared as extras in the root `pyproject.toml`; each solution's `requirements.txt` mirrors its extra.

## Safety Notes

- `UFRobot(config)` connects to the controller and moves to `start_joints` on construction — instantiating it drives the robot.
- `send_action()` returns the controller error code; callers should check it in their loop and exit on a non-zero value, as the solution scripts do.
- Lower `robot_speed` and `robot_acc` for the first run, and keep someone at the emergency stop.
