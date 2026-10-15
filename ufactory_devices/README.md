# ufactory_devices

The shared core library for all five teleoperation solutions. Each solution's own script handles only the loop of "read input → compute mapping → send action"; everything that talks to hardware lives here: the xArm wrapper and the drivers for four input devices.

## Directory Structure

```
ufactory_devices/
├── robot/
│   └── uf_robot.py            # UFRobot: xArm connection, motion, gripper control
├── pika/
│   └── pika_device.py         # PikaDevice: Pika Sense / Pika Gripper serial driver
├── umi/
│   ├── xvlib/
│   │   ├── xvlib.py           # XVLib: ctypes wrapper around libxvlib.so
│   │   ├── libxvlib.so        # Libraries bundled with the repository (Linux x86_64)
│   │   ├── libopencv_core.so.4.2
│   │   ├── libopencv_imgproc.so.4.2
│   │   └── libtbb.so.2
│   └── vive_tracker/
│       ├── vive_tracker.py    # ViveTracker: HTC Vive Tracker driver built on pysurvive
│       └── transformations.py # Transformations: pose math utilities
├── xbox/
│   └── xbox_device.py         # XBoxDevice: Xbox-compatible gamepad driver
└── spacemouse/
    └── space_device.py        # SpaceDevice: 3Dconnexion SpaceMouse driver
```

The top-level `__init__.py` is empty — import from the subpackages explicitly, for example `from ufactory_devices.robot import UFRobot`.

## Modules Used by Each Solution

| Teleoperation Solution | Imported from ufactory_devices |
| --- | --- |
| [pika_teleop](../pika_teleop/README.md) | `robot.UFRobot`, `pika.PikaDevice`, `umi.Transformations` |
| [umi_teleop](../umi_teleop/README.md) | `robot.UFRobot`, `umi.XVLib`, `umi.Transformations` |
| [gello_teleop](../gello_teleop/README.md) | `robot.UFRobot` |
| [xbox_teleop](../xbox_teleop/README.md) | `robot.UFRobot`, `xbox.XBoxDevice` |
| [spacemouse_teleop](../spacemouse_teleop/README.md) | `robot.UFRobot`, `spacemouse.SpaceDevice` |

## robot/ — xArm Wrapper

`from ufactory_devices.robot import UFRobotConfig, UFRobot`

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

- `UFRobot(config)` — on construction it connects to the controller, enables the motors, clears errors, and moves to `start_joints`. **Instantiating it moves the robot**, so confirm the workspace first.
- `send_action(action)` — the common dispatch interface used by every solution, split by `robot_mode`:
  - `robot_mode: 6`: `action[:axis_count]` are joint angles (radians), `action[axis_count]` is the normalized gripper value (0 open → 1 closed).
  - `robot_mode: 7` and others: `action[:6]` is `[x, y, z, rx, ry, rz]`, `action[6]` is the normalized gripper value.
  - The gripper is driven over TDK Modbus (xArm Gripper G1/G2, BIO Gripper G2, Robotiq) or serial (Pika Gripper), depending on type.
  - Returns the controller error code; callers should check it in their loop and exit on a non-zero value.
- `get_position(is_axis_angle=False)` — read the current pose (xyzrpy by default, or axis-angle).
- `robot_init(enable=True, init_gripper_pose=False)` — reset mode and state, optionally initializing the gripper.

`uf_robot.py` imports `PikaDevice` at module level, so `import ufactory_devices.robot` also pulls in the `pika` subpackage; `agx-pypika` itself is imported lazily, so it is not needed when no Pika gripper is used.

## pika/ — Pika Sense and Pika Gripper

`from ufactory_devices.pika import PikaDevice`

- `get_serial_ports(vidpid='1a86:7522')` — enumerate candidate serial ports by VID:PID.
- `check_pika_device(port)` — probe which device is on a port. Returns `-1` port cannot be opened, `0` not a Pika device, `1` Pika Sense, `2` Pika Gripper.
- `PikaDevice(dev_type=1, pika_sense_port=None, pika_gripper_port=None)` — `dev_type` is `1` for Sense only, `2` for Gripper only, `3` for both. Ports left unset are discovered by scanning and probing.
- The `pika_sense` / `pika_gripper` properties connect only on first access. Handles for the same port are reused through the class-level `PIKA_DEVICE_MAP`, so `UFRobot`'s Pika gripper and a teleoperation script can share one Sense instance.

Requires `agx-pypika` (which provides the `pika.sense` / `pika.gripper` modules), imported lazily inside the properties.

## umi/ — FastUMI and Vive Tracker

`from ufactory_devices.umi import XVLib, Transformations` / `from ufactory_devices.umi import ViveTracker`

### xvlib/

`XVLib(serial_number, init_slam=False, init_clamp_stream=False, init_color_camera=False, init_fisheye_cameras=False)`

A ctypes wrapper around `libxvlib.so` that enumerates devices and initializes the data streams on demand. The calls teleoperation uses most:

- `xv_get_devices()` — enumerate connected FastUMI devices.
- `xv_get_slam_pose()` / `xv_get_slam_data()` — read the built-in SLAM pose.
- `xv_get_clamp_stream_data()` — read gripper open/close data.
- `xv_get_color_camera_data()` / `xv_get_fisheye_cameras_data()` — read camera frames as numpy arrays (requires `opencv-python`).

Loading order is: check the system XVSDK → preload `libtbb.so.2` → load `libopencv_*.so` → load `libxvlib.so`. These `.so` files are bundled with the repository as a fallback; the bundled `libopencv_core.so.4.2` depends on the old TBB ABI, which is incompatible with the oneAPI TBB (`libtbb.so.12`) shipped in Ubuntu 22.04+, so the code preloads `libtbb.so.2` explicitly. If the XVSDK is not installed system-wide, it raises with the install command.

### vive_tracker/

- `ViveTracker(config_path=None, lh_config=None, args=None)` — a singleton (`SingletonMeta`) that collects poses on a background thread. `get_pose(device_name=None)` returns a pose, `get_raw_pose()` the raw pose, `get_tracked_device_names()` lists tracked devices, and `stop()` / `close()` release resources.
- `Transformations` — a static utility class: conversions between quaternions, rotation matrices, RPY, and axis-angle, plus `tracker_pose_to_robot_matrix()` / `tracker_robot_matrix_to_robot_pose()` for mapping tracker poses to robot poses.

Note that `transformations.py` lives under `umi/vive_tracker/` rather than at the top level; `umi.Transformations` re-exports it from there, and pika_teleop uses it for pose conversion as well.

## xbox/ — Xbox-Compatible Gamepad

`from ufactory_devices.xbox import XBoxDevice`

- `XBoxDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.2, 0.2, 0.1], logger=None)` — a `threading.Thread` subclass with a daemon thread reading gamepad input continuously.
- Prefers `evdev` on Linux when installed, falling back to the `inputs` package otherwise.
- `connected` reports the connection state; `state` exposes sticks, triggers, buttons, and the D-pad; `set_axes_deadzone()` adjusts deadzones at runtime.

## spacemouse/ — 3Dconnexion SpaceMouse

`from ufactory_devices.spacemouse import SpaceDevice`

- `SpaceDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.15, 0.15, 0.1], logger=None)` — likewise a background thread.
- HID backend: non-Windows platforms always use HIDAPI; on Windows, the `SPACEMOUSE_BACKEND` environment variable selects `hidapi`, `hid`, or `pywinusb`, defaulting to `pywinusb` with a HIDAPI fallback.
- `list_space_devices()` lists available devices; `connected`, `product_name`, `vendor_name`, `vendor_id`, and `product_id` describe the device; `state` exposes the six axes and buttons; `set_led(state)` controls the indicator LED; `register_state_changed_callback(cb)` registers a state callback.

## Dependencies

| Module | Dependency | Notes |
| --- | --- | --- |
| `robot/` | `xarm-python-sdk` | Shared by every solution. |
| `pika/` | `agx-pypika`, `pyserial` | `agx-pypika` provides the `pika` module; only needed when a Pika Sense/Gripper is actually used. |
| `umi/xvlib/` | system XVSDK (`libxvsdk.so`), `opencv-python` | The deb install command is printed when the XVSDK is missing; camera frames need OpenCV. |
| `umi/vive_tracker/` | `pysurvive` | Only needed when an HTC Vive Tracker is used. |
| `xbox/` | `inputs`, optionally `evdev` on Linux | `evdev` is preferred when present. |
| `spacemouse/` | `hidapi` (import name `hid`), optionally `pywinusb` on Windows | See the backend selection rules above. |

Each solution's `requirements.txt` lists only what that solution uses; see the root [README.md](../README.md) for installation.

## Safety Notes

- `UFRobot(config)` connects to the controller and moves to `start_joints` on construction — instantiating it drives the robot.
- `send_action()` returns the controller error code; callers should check it in their loop and exit on a non-zero value, as the solution scripts do.
- Lower `robot_speed` and `robot_acc` for the first run, and keep someone at the emergency stop.
