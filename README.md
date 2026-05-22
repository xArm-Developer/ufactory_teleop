# UFACTORY Teleoperation System

This project provides teleoperation solutions for UFACTORY (深圳市众为创造科技有限公司) robotic arms, featuring three independent approaches:

1. **Pika Sense-based Teleoperation**: Utilizing Agilex Robotics' Pika Sense technology for precise motion tracking and control.
[![Watch the video](assets/pika_teleoperation_system.jpg)](https://www.youtube.com/watch?v=D4L1dyyBriA)
2. **UMI Teleoperation**: Using FAST UMI devices for motion capture and control.
3. **GELLO-inspired Framework**: Based on concepts from the open-source GELLO framework (https://wuphilipp.github.io/gello_site/)
[![Watch the video](assets/gello.png)](https://www.youtube.com/watch?v=wTiWLiHciT8)

## Overview

The UFACTORY Teleoperation System enables intuitive remote control of UFACTORY robotic arms through advanced motion tracking technologies. These systems are designed to lower the barrier to collecting high-quality demonstration data for robotic learning and manipulation tasks.

## Project Structure

```
ufactory_teleop/
├── ufactory_devices/         # Shared core library
│   ├── transformations.py    # Pose math (quaternion, RPY, axis-angle, homogeneous matrices)
│   ├── robot/                # xArm robot wrapper (connection, motion, gripper control)
│   ├── pika/                 # Pika Sense & Pika Gripper serial driver
│   ├── umi/                  # UMI device SDK bindings (XVLib via ctypes)
│   └── vive_tracker/         # HTC Vive Tracker driver (pysurvive)
├── pika_teleop/              # Pika Sense teleoperation solution
│   ├── uf_robot_pika_teleop.py
│   ├── calibrate.py
│   ├── config/
│   └── rules/
├── umi_teleop/               # UMI teleoperation solution
│   ├── uf_robot_umi_teleop.py
│   ├── uf_robot_umi_teleop_dual.py
│   ├── calibrate.py
│   ├── config/
│   ├── rules/
│   └── xvsdk/
└── gello_teleop/             # Gello teleoperation solution
    ├── uf_robot_gello_teleop.py
    ├── config/
    └── rules/
```

## Teleoperation Solutions

### Pika Sense-based Solution

Uses Agilex Robotics' Pika Sense — a handheld clamp controller with integrated Vive Tracker mount — to capture 6-DOF hand motion and map it to robot end-effector movement in real time.

- **Tracking**: HTC Vive Tracker + Lighthouse base stations (via Pika SDK)
- **Control**: Single-arm teleoperation with command-state toggle (clamp open/close to start/stop)
- **Gripper Support**: Pika Gripper, xArm Gripper (G1/G2), BIO Gripper G2, Robotiq Gripper
- **Motion Modes**: Servo Cartesian (mode 1) and online trajectory planning (mode 7)

For details, see [pika_teleop/README.md](pika_teleop/README.md).

### UMI Teleoperation Solution

Using FAST UMI devices for low-cost, intuitive teleoperation. Supports both single-arm and dual-arm setups with flexible tracking options.

- **Tracking**: UMI built-in SLAM or HTC Vive Tracker + Lighthouse base stations (configurable)
- **Control**: Single-arm (`uf_robot_umi_teleop.py`) and dual-arm (`uf_robot_umi_teleop_dual.py`) teleoperation
- **Gripper Support**: xArm Gripper G2, xArm Gripper, BIO Gripper G2, Pika Gripper, Robotiq Gripper
- **Motion Modes**: Servo Cartesian (mode 1) and online trajectory planning (mode 7)
- **Dual-Arm**: Two UMI devices control two xArm robots simultaneously via independent threads

For details, see [umi_teleop/README.md](umi_teleop/README.md).

### Gello Teleoperation Solution

A joint-space teleoperation system using the Gello leader arm (Dynamixel servo-based haptic input device) to control xArm robots. Joint positions are read via serial port, and auto-offset calibration maps them to robot target joint angles.

- **Control Space**: Joint space (robot_mode: 6), directly mapping leader arm joint motion
- **Supported Robots**: xArm5, xArm6, xArm7 (with corresponding example configs)
- **Joint Mapping**: Configurable via `joint_ids` and `joint_signs` for flexible Gello-to-robot mapping
- **Auto-Offset**: Automatically reads Gello's current pose at startup and computes joint offsets
- **Torque Mode**: Unmapped Dynamixel joints can be held via `torque_joint_ids` with torque enabled
- **Gripper Support**: Optional Gello-side Dynamixel gripper, supports xArm Gripper (G1/G2), Pika Gripper, Robotiq Gripper

For details, see [gello_teleop/README.md](gello_teleop/README.md).

## Features

- **Intuitive Control**: Direct manipulation interfaces that reduce the gap between user and robot embodiment
- **Cost-Effective**: Leverages commercially available tracking technologies and off-the-shelf components
- **High-Quality Demonstrations**: Enables collection of precise demonstration data for imitation learning
- **Multi-Robot Support**: Compatible with various UFACTORY robotic arm models (xArm 5/6/7, Lite 6, 850)
- **Flexible Gripper Options**: Supports xArm Gripper (G1/G2), BIO Gripper G2, Pika Gripper, and Robotiq Gripper
- **Dual-Arm Operation**: UMI solution supports synchronized dual-arm teleoperation for bimanual tasks

## Getting Started

### Pika Sense-based Teleoperation

Please refer to the detailed documentation in [pika_teleop/README.md](pika_teleop/README.md).

Quick start:

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/pika_teleop
conda create --name py39 python=3.9
conda activate py39
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
python uf_robot_pika_teleop.py --config config/xarm6_pika_teleop.yaml
```

### UMI Teleoperation

Please refer to the detailed documentation in [umi_teleop/README.md](umi_teleop/README.md).

Quick start (single arm):

```bash
cd ufactory_teleop/umi_teleop
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

Quick start (dual arm):

```bash
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

### Gello Teleoperation

Please refer to the detailed documentation in [gello_teleop/README.md](gello_teleop/README.md).

Quick start:

```bash
cd ufactory_teleop/gello_teleop
conda create --name py39 python=3.9
conda activate py39
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
git clone https://github.com/wuphilipp/gello_software.git /tmp/gello_software
cd /tmp/gello_software
pip install -e .
cd -
sudo usermod -aG dialout $USER
# Re-login then run
python uf_robot_gello_teleop.py --config config/xarm7_gello_teleop.yaml
```

## References

- [Agilex Robotics Pika Sense](https://global.agilex.ai/products/pika)
- [UFACTORY Robotic Arms](https://www.ufactory.cc/xarm-collaborative-robot/)
- [LuMos FastUMI](https://www.fastumi.com/)
- [GELLO: General Low-Cost Teleoperation Framework](https://wuphilipp.github.io/gello_site/)
