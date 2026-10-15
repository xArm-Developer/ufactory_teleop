# UFACTORY Teleoperation System

This project provides teleoperation solutions for UFACTORY (深圳市众为创造科技有限公司) robotic arms, enabling intuitive remote control through motion tracking technologies.   

It is designed to lower the barrier to collecting high-quality demonstration data for robotic learning and manipulation tasks, and supports a range of arm models including xArm 5/6/7, Lite 6, and 850. All five solutions share the robot wrapper and device drivers in [ufactory_devices](ufactory_devices/README.md).

[中文](README_ZH.md) | [Pika](#1-pika-sense-teleoperation) | [UMI](#2-umi-teleoperation) | [Gello](#3-gello-teleoperation) | [Xbox](#4-xbox-controller-teleoperation) | [SpaceMouse](#5-spacemouse-teleoperation)

Five independent solutions are available:

| Solution | Input Device | Control Space | External Tracking | End Effector |
| --- | --- | --- | --- | --- |
| [Pika Sense Teleoperation](pika_teleop/README.md) | Pika Sense handheld clamp | Cartesian | Required: Vive Tracker + Lighthouse base stations | xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, Robotiq Gripper |
| [UMI Teleoperation](umi_teleop/README.md) | FastUMI | Cartesian (single/dual arm) | Optional: UMI built-in SLAM or Vive Tracker | xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, Robotiq Gripper |
| [Gello Teleoperation](gello_teleop/README.md) | Gello leader arm (Dynamixel servos) | Joint | None | xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, Robotiq Gripper (plus optional Gello-side Dynamixel gripper) |
| [Xbox Controller Teleoperation](xbox_teleop/README.md) | Xbox-compatible gamepad | Cartesian | None | Gripper not controlled |
| [SpaceMouse Teleoperation](spacemouse_teleop/README.md) | 3Dconnexion SpaceMouse | Cartesian | None | Gripper not controlled |

## Get the Code

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop
```

The commands in each solution below are run from the repository root.

## 1. Pika Sense Teleoperation

Uses Agilex Robotics' Pika Sense — a handheld clamp controller with integrated Vive Tracker mount — to capture 6-DOF hand motion and map it to robot end-effector movement in real time.

[![Watch the video](https://i.ytimg.com/vi/D4L1dyyBriA/maxresdefault.jpg)](https://www.youtube.com/watch?v=D4L1dyyBriA)

- **Tracking**: HTC Vive Tracker + Lighthouse base stations (via Pika SDK)
- **Control**: Single-arm teleoperation with command-state toggle (clamp open/close to start/stop)
- **Gripper Support**: xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, Robotiq Gripper
- **Motion Modes**: Servo Cartesian (mode 1) and online trajectory planning (mode 7)

```bash
cd pika_teleop
conda create --name py39 python=3.9
conda activate py39
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
python uf_robot_pika_teleop.py --config config/xarm6_pika_teleop.yaml
```

See [pika_teleop/README.md](pika_teleop/README.md) for calibration, configuration parameters, and troubleshooting.

## 2. UMI Teleoperation

Uses FastUMI devices for intuitive teleoperation, with support for both single-arm and dual-arm setups and flexible tracking options.

[![Watch the video](https://i.ytimg.com/vi/qlVHa8qA6oo/maxresdefault.jpg)](https://youtu.be/qlVHa8qA6oo)

- **Tracking**: UMI built-in SLAM or HTC Vive Tracker + Lighthouse base stations (configurable)
- **Control**: Single-arm (`uf_robot_umi_teleop.py`) and dual-arm (`uf_robot_umi_teleop_dual.py`) teleoperation
- **Gripper Support**: xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, Robotiq Gripper
- **Motion Modes**: Servo Cartesian (mode 1) and online trajectory planning (mode 7)
- **Dual-Arm**: Two UMI devices control two xArm robots simultaneously via independent threads

Single arm:

```bash
cd umi_teleop
conda create --name py39 python=3.9
conda activate py39
sudo dpkg -i xvsdk/XVSDK_focal_amd64.deb
sudo apt install -y --fix-broken
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
python uf_robot_umi_teleop.py --config config/xarm6_umi_teleop.yaml
```

Dual arm (after the installation above):

```bash
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

See [umi_teleop/README.md](umi_teleop/README.md) for calibration, configuration parameters, and troubleshooting.

## 3. Gello Teleoperation

A joint-space teleoperation system using the Gello leader arm (Dynamixel servo-based haptic input device) to control xArm robots. Joint positions are read via serial port, and auto-offset calibration maps them to robot target joint angles.

[![Watch the video](https://i.ytimg.com/vi/wTiWLiHciT8/maxresdefault.jpg)](https://www.youtube.com/watch?v=wTiWLiHciT8)

- **Control Space**: Joint space (robot_mode: 6), directly mapping leader arm joint motion
- **Supported Robots**: xArm5, xArm6, xArm7 (with corresponding example configs)
- **Joint Mapping**: Configurable via `joint_ids` and `joint_signs` for flexible Gello-to-robot mapping
- **Auto-Offset**: Automatically reads Gello's current pose at startup and computes joint offsets
- **Torque Mode**: Unmapped Dynamixel joints can be held via `torque_joint_ids` with torque enabled
- **Gripper Support**: Optional Gello-side Dynamixel gripper, supports xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, Robotiq Gripper

```bash
cd gello_teleop
conda create --name py39 python=3.9
conda activate py39
pip install -r requirements.txt
sudo usermod -aG dialout $USER
# Re-login then run
python uf_robot_gello_teleop.py --config config/xarm7_gello_teleop.yaml
```

Place the Gello leader arm at the reference pose matching `TeleoperatorConfig.start_joints` before running. See [gello_teleop/README.md](gello_teleop/README.md) for pose alignment, configuration parameters, and troubleshooting.

## 4. Xbox Controller Teleoperation

Use an Xbox-compatible gamepad for six-axis Cartesian end-effector control. The controller driver supports Linux (preferring `evdev` when installed) and platforms supported by the `inputs` package.

[![Watch the video](https://i.ytimg.com/vi/SlesYwthPCw/maxresdefault.jpg)](https://youtu.be/SlesYwthPCw)

- **Activation**: Hold `START` + `SELECT` for 0.5 seconds to activate or deactivate control
- **Motion**: Use the sticks and triggers for Cartesian translation and rotation; the D-pad adjusts the Z/Yaw direction
- **Axis selection**: `X`/`Y` select translation axes, while `A`/`B` select rotation axes
- **Quick actions**: Hold `START` to level the tool or hold `SELECT` to return the robot to its home position; a short `START` press reverses the Z/Yaw direction

```bash
cd xbox_teleop
pip install -r requirements.txt
# Edit config/xarm6_xbox_teleop.yaml for your robot
python uf_robot_xbox_teleop.py --config config/xarm6_xbox_teleop.yaml
```

See [xbox_teleop/README.md](xbox_teleop/README.md) for button mappings and configuration parameters.

## 5. SpaceMouse Teleoperation

Use a supported 3Dconnexion SpaceMouse as a six-degree-of-freedom input device for Cartesian end-effector control. 

[![Watch the video](https://i.ytimg.com/vi/uFnOfiycf7k/maxresdefault.jpg)](https://youtu.be/uFnOfiycf7k)

- **Activation**: Hold the left and right device buttons together for 0.5 seconds to activate or deactivate control
- **Quick actions**: Hold the left button to level the tool or the right button to return the robot to its home position
- **HID backend**: Uses HIDAPI on Linux and macOS. On Windows, `pywinusb` is preferred when installed, with HIDAPI as a fallback; `SPACEMOUSE_BACKEND` can select the Windows backend

```bash
cd spacemouse_teleop
pip install -r requirements.txt
# Edit config/xarm6_spacemouse_teleop.yaml for your robot
python uf_robot_spacemouse_teleop.py --config config/xarm6_spacemouse_teleop.yaml
```

See [spacemouse_teleop/README.md](spacemouse_teleop/README.md) for button mappings and configuration parameters.

## References

- [Agilex Robotics Pika Sense](https://global.agilex.ai/products/pika)
- [UFACTORY Robotic Arms](https://www.ufactory.cc/xarm-collaborative-robot/)
- [LuMos FastUMI](https://www.fastumi.com/)
- [GELLO: General Low-Cost Teleoperation Framework](https://wuphilipp.github.io/gello_site/)
- [Xbox 360 Controller (Windows setup and drivers)](https://www.xbox.com/en-US/accessories)
- [3Dconnexion SpaceMouse Wireless](https://3dconnexion.com/us/product/spacemouse-wireless/)
