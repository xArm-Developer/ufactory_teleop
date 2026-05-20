# Pika Teleoperation System

Use Agilex Robotics' Pika Sense (https://global.agilex.ai/products/pika) for teleoperation control of UFACTORY's robotic arms (https://www.ufactory.cc/xarm-collaborative-robot/).

GitHub: https://github.com/xArm-Developer/ufactory_teleop


[![Watch the video](../assets/pika_teleoperation_system.jpg)](https://www.youtube.com/watch?v=D4L1dyyBriA)

This guide is based on `pika_teleop/uf_robot_pika_teleop.py`. It explains how to use Pika Sense, Vive Tracker, and a UFACTORY xArm robot for Cartesian teleoperation.

## 1. Overview

The entry script reads the pose of the Vive Tracker exposed through Pika Sense, converts the tracker motion into a robot end-effector target pose, and sends the action to the robot through `UFRobot`.

Main components:

- `pika_teleop/uf_robot_pika_teleop.py`: Pika Sense teleoperation entry script.
- `ufactory_devices/pika/pika_device.py`: Pika Sense and Pika Gripper serial detection and connection helper.
- `ufactory_devices/robot/uf_robot.py`: xArm connection, initialization, motion, and gripper control wrapper.
- `ufactory_devices/transformations.py`: pose, quaternion, RPY, axis-angle, and relative-motion transforms.

The script supports:

- Pika Sense serial auto-detection.
- Vive Tracker pose tracking through Pika SDK.
- Command-state based start/stop control.
- Optional gripper control from Pika Sense gripper distance.
- xArm motion mode `7` by default, using axis-angle Cartesian targets.

## 2. Requirements

Recommended system:

- Ubuntu 22.04 or Ubuntu 24.04.
- Python 3.8, 3.9, or 3.10.
- UFACTORY xArm robot.
- Pika Sense.
- Vive Tracker and Lighthouse base stations.
- Optional Pika Gripper or other supported xArm-compatible grippers.

## 3. Installation

Clone the repository and enter the Pika teleoperation folder:

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/pika_teleop
```

Create and activate a virtual environment:

```bash
conda create --name py39 python=3.9
conda activate py39
```

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
```

After installation, verify the following imports work:

```bash
python -c "import pysurvive;from pika.sense import Sense;from pika.gripper import Gripper;from xarm.wrapper import XArmAPI"
```

Install USB and device rules:

```bash
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug and reconnect Pika Sense, Vive Tracker, and Pika Gripper after reloading udev rules.

## 4. Configuration

Example configuration:

```bash
pika_teleop/config/xarm6_pika_teleop.yaml
```

```yaml
RobotConfig:
  robot_ip: "192.168.1.195"
  gripper_type: 10
  start_joints: [0, 0, 0, 0, 0, 0]
  start_tcp_pose: [300, 0, 300, 3.1415927, 0, 0]

TeleoperatorConfig:
  # pika_sense_port: "/dev/ttyUSB0"
  # vive_tracker_id: "WM0"
  use_gripper: True
  tracker_to_robot_eef: [0, 0, 0, 3.1415927, -1.570796, 0]
```

### RobotConfig

| Field | Description |
| --- | --- |
| `robot_ip` | Robot controller IP address. |
| `robot_mode` | Motion mode. `1` means servo Cartesian mode; `7` means online Cartesian trajectory planning mode. Default is `7`. |
| `robot_speed` | Cartesian motion speed. Default is `250`. |
| `robot_acc` | Cartesian motion acceleration. Default is `1000`. |
| `gripper_type` | Gripper type. `0`: none, `1`: xArm Gripper, `2`: xArm Gripper G2, `3`: BIO Gripper G2, `10`: Pika Gripper, `11`: Robotiq Gripper. |
| `gripper_port` | Pika Gripper serial port. Used only when `gripper_type: 10`. If omitted, the code tries to auto-detect it. |
| `gripper_speed` | Gripper speed. `-1` uses the wrapper default. |
| `gripper_force` | Gripper force. `-1` uses the wrapper default. |
| `start_joints` | Joint angles used during startup, in radians. |
| `start_tcp_pose` | Optional TCP pose after `start_joints`, in `[x, y, z, roll, pitch, yaw]`, with position in mm and orientation in radians. |

### TeleoperatorConfig

| Field | Description |
| --- | --- |
| `fps` | Control loop frequency. Default is `30`. |
| `use_gripper` | Whether to read Pika Sense gripper distance and append a gripper command to the robot action. |
| `pika_sense_port` | Pika Sense serial port, for example `/dev/ttyUSB0`. If omitted, `PikaDevice` scans serial devices with VID/PID `1a86:7522`. |
| `vive_tracker_id` | Vive Tracker ID used by `pika_sense.get_pose()`. Default is `WM0`. Use the actual `LHR-...` ID if needed. |
| `tracker_to_robot_eef` | Transform from tracker/Pika frame to robot end-effector frame, in `[x, y, z, roll, pitch, yaw]`. |

## 5. Vive Tracker Calibration

Run calibration before first use or whenever Lighthouse base stations move:

```bash
cd ufactory_teleop/pika_teleop
python calibrate.py
```

The calibration script removes `~/.config/libsurvive/config.json`, runs `pysurvive` with force calibration, and prints detected tracker poses. Keep base stations and trackers still during calibration.

## 6. Running

Run from the Pika teleoperation folder:

```bash
cd ufactory_teleop/pika_teleop
python uf_robot_pika_teleop.py --config config/xarm6_pika_teleop.yaml
```

Startup sequence:

1. Load the YAML configuration.
2. Connect to the robot.
3. Move the robot to `start_joints`, then optionally to `start_tcp_pose`.
4. Connect Pika Sense and initialize Vive Tracker.
5. Wait for `Enter to control robot with teleop >>>`.
6. Enter the control loop after pressing Enter.

The script uses Pika Sense command state changes to start and stop teleoperation. In normal operation, quickly opening/closing the Pika Sense clamp changes the command state.

## 7. Safety Notes

- Keep the robot workspace clear before launching the script.
- The robot moves during initialization before teleoperation begins.
- Verify `start_joints` and `start_tcp_pose` at low speed first.
- Keep an operator near the emergency stop during testing.
- Start with conservative `robot_speed` and `robot_acc`.
- Keep Pika Sense still when starting control, because the first pose defines the teleoperation reference.

