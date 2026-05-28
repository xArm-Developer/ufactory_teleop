# UMI Teleoperation Guide

Use LuMos FastUMI Pro (https://lumosumi.lumosbot.tech/pro/) for teleoperation control of UFACTORY's robotic arms (https://www.ufactory.cc/xarm-collaborative-robot/).

GitHub: https://github.com/xArm-Developer/ufactory_teleop  

This guide is based on `umi_teleop/uf_robot_umi_teleop.py` and `umi_teleop/uf_robot_umi_teleop_dual.py`. It explains how to use UMI devices to teleoperate one or two UFACTORY xArm robots.

## 1. Overview

The UMI teleoperation scripts read either UMI SLAM pose or Vive Tracker pose, convert relative hand motion into a robot end-effector target pose, and send actions to the robot through `UFRobot`.

Entry scripts:

- `umi_teleop/uf_robot_umi_teleop.py`: one UMI device controls one robot.
- `umi_teleop/uf_robot_umi_teleop_dual.py`: two UMI devices control two robots, using two background threads.

Supported pose sources:

- `use_vive_tracker: True`: use Vive Tracker pose directly.
- `use_vive_tracker: False`: use UMI SLAM pose directly.

## 2. Requirements

Recommended system:

- Ubuntu 22.04 or Ubuntu 24.04.
- Python 3.8, 3.9, or 3.10.
- UFACTORY xArm robot.
- FAST UMI / UMI device.
- Optional Vive Tracker and Lighthouse base stations.
- Optional supported gripper.

## 3. Installation

Clone the repository and enter the UMI teleoperation folder:

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/umi_teleop
```

Create and activate a virtual environment:

```bash
conda create --name py39 python=3.9
conda activate py39
```

Install XVSDK:

```bash
sudo dpkg -i xvsdk/XVSDK_focal_amd64.deb
sudo apt install -y --fix-broken
```

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
```

```bash
python -c "import cv2;import pysurvive;from pika.gripper import Gripper;from xarm.wrapper import XArmAPI"
```

Install USB rules:

```bash
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug and reconnect UMI and Vive devices after reloading udev rules.

For multiple UMI devices, increase the USB buffer:

```bash
sudo sed -i '/GRUB_CMDLINE_LINUX_DEFAULT/s/quiet splash/quiet splash usbcore.usbfs_memory_mb=128/' /etc/default/grub
sync
sudo update-grub
sudo reboot
```

## 4. Configuration

Example files:

- Single robot: `umi_teleop/config/xarm6_umi_teleop.yaml`
- Dual robot: `umi_teleop/config/xarm6_umi_teleop_dual.yaml`

### Single-Robot YAML

```yaml
RobotConfig:
  robot_ip: "192.168.1.29"
  gripper_type: 2
  start_joints: [0, 0, 0, -3.1415927, 1.570796, -1.570796]
  start_tcp_pose: [350, 0, 250, -1.570796, 0, -1.570796]

TeleoperatorConfig:
  serial_number: "250801DR48FP26001318"
  use_vive_tracker: True
  vive_tracker_id: "LHR-555DC7BF"
  use_gripper: True
  tracker_to_robot_eef: [0, 0, 0, 0, 0, -1.570796]
  robot_base_pose: [350, 0, 250, -1.570796, 0, -1.570796]
```

### Dual-Robot YAML

The dual script expects top-level `L` and `R` sections. Each section must contain its own `RobotConfig` and `TeleoperatorConfig`.

```yaml
L:
  RobotConfig:
    robot_ip: "192.168.1.29"
    gripper_type: 2
    start_joints: [0, 0, 0, -3.1415927, 1.570796, -1.570796]
    start_tcp_pose: [350, 0, 250, -1.570796, 0, -1.570796]
  TeleoperatorConfig:
    serial_number: "250801DR48FP26001318"
    use_vive_tracker: True
    vive_tracker_id: "LHR-555DC7BF"
    use_gripper: True
    tracker_to_robot_eef: [0, 0, 0, 0, 0, -1.570796]
    robot_base_pose: [350, 0, 250, -1.570796, 0, -1.570796]

R:
  RobotConfig:
    robot_ip: "192.168.1.195"
    gripper_type: 2
    start_joints: [0, 0, 0, -3.1415927, 1.570796, -1.570796]
    start_tcp_pose: [350, 0, 250, -1.570796, 0, -1.570796]
  TeleoperatorConfig:
    serial_number: "250801DR48FP26001295"
    use_vive_tracker: True
    vive_tracker_id: "LHR-2425BAD3"
    use_gripper: True
    tracker_to_robot_eef: [0, 0, 0, 0, 0, 1.570796]
    robot_base_pose: [350, 0, 250, -1.570796, 0, -1.570796]
```

## 5. Parameter Reference

### RobotConfig

| Field | Description |
| --- | --- |
| `robot_ip` | Robot controller IP address. |
| `robot_mode` | Motion mode. `1`: servo Cartesian mode; `7`: online Cartesian trajectory planning mode. Default is `7`. |
| `robot_speed` | Cartesian motion speed. Default is `250`. |
| `robot_acc` | Cartesian motion acceleration. Default is `1000`. |
| `gripper_type` | `0`: none, `1`: xArm Gripper, `2`: xArm Gripper G2, `3`: BIO Gripper G2, `10`: Pika Gripper, `11`: Robotiq Gripper. |
| `gripper_port` | Pika Gripper serial port, only used with `gripper_type: 10`. |
| `gripper_speed` | Gripper speed. `-1` uses the default. |
| `gripper_force` | Gripper force. `-1` uses the default. |
| `start_joints` | Startup joint angles in radians. |
| `start_tcp_pose` | Optional startup TCP pose in `[x, y, z, roll, pitch, yaw]`, with position in mm and orientation in radians. |

### TeleoperatorConfig

| Field | Description |
| --- | --- |
| `serial_number` | UMI device serial number. Required. |
| `fps` | Control loop frequency. Default is `30`. |
| `use_gripper` | Whether to read UMI clamp stream and append a gripper command. |
| `use_vive_tracker` | Whether to use Vive Tracker pose. If false, UMI SLAM pose is used. |
| `vive_tracker_id` | Vive Tracker ID, for example `LHR-555DC7BF`. |
| `tracker_to_robot_eef` | Transform from tracker/UMI frame to robot end-effector frame. |
| `robot_base_pose` | Robot reference end-effector pose used as the teleoperation base pose. |

## 6. Vive Tracker Calibration

Run calibration before first use or after moving Lighthouse base stations:

```bash
cd ufactory_teleop/umi_teleop
python calibrate.py
```

The script removes `~/.config/libsurvive/config.json`, forces calibration, and prints detected tracker poses. Keep base stations and trackers still during calibration.

## 7. Running

Single robot:

```bash
cd ufactory_teleop/umi_teleop
python uf_robot_umi_teleop.py --config config/xarm6_umi_teleop.yaml
```

Dual robot:

```bash
cd ufactory_teleop/umi_teleop
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

Startup sequence:

1. Load YAML configuration.
2. Connect and initialize robot or robots.
3. Move each robot to `start_joints`, then optionally `start_tcp_pose`.
4. Initialize UMI and optional Vive Tracker.
5. Wait for `Enter to control robot with teleop >>>`.
6. Press Enter to start teleoperation.


## 8. Safety Notes

- The robot moves during initialization before teleoperation starts.
- Verify `start_joints`, `start_tcp_pose`, and `robot_base_pose` at low speed first.
- Keep the workspace clear and keep an operator near the emergency stop.
- For dual robot operation, verify left and right `robot_ip`, `serial_number`, `vive_tracker_id`, and `tracker_to_robot_eef` before pressing Enter.

