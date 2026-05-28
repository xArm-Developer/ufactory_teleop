# UFACTORY 遥操作系统

本项目为 UFACTORY (深圳市众为创造科技有限公司) 机械臂提供遥操作解决方案，包含三套独立方案：

1. **基于 Pika Sense 的遥操作**：利用 Agilex Robotics 的 Pika Sense 技术实现精准运动跟踪与控制。
[![观看视频](assets/pika_teleoperation_system.jpg)](https://www.bilibili.com/video/BV1791rB4Egk/?spm_id_from=333.1387)
2. **UMI 遥操作**：使用 FAST UMI 设备进行运动捕捉与控制。
[![观看视频](assets/fastumi.jpg)](https://www.bilibili.com/video/BV1qAGm6fEZE/?spm_id_from=333.1387)
3. **基于 GELLO 的遥操作框架**：基于开源 GELLO 框架（https://wuphilipp.github.io/gello_site/）的理念  
[![观看视频](assets/gello.png)](https://www.bilibili.com/video/BV12xFjzzEaX/?spm_id_from=333.1387)

## 概述

UFACTORY 遥操作系统通过先进的运动跟踪技术，实现对 UFACTORY 机械臂的直观远程控制。该系统旨在降低高质量示教数据采集的门槛，服务于机器人学习和操作任务。

## 项目结构

```
ufactory_teleop/
├── ufactory_devices/         # 共享核心库
│   ├── transformations.py    # 位姿数学工具（四元数、RPY、轴角、齐次矩阵）
│   ├── robot/                # xArm 机械臂封装（连接、运动、夹爪控制）
│   ├── pika/                 # Pika Sense 与 Pika Gripper 串口驱动
│   ├── umi/                  # UMI 设备 SDK 绑定（基于 ctypes 的 XVLib 封装）和 HTC Vive Tracker 驱动（pysurvive）
├── pika_teleop/              # Pika Sense 遥操作方案
│   ├── uf_robot_pika_teleop.py
│   ├── calibrate.py
│   ├── config/
│   └── rules/
├── umi_teleop/               # UMI 遥操作方案
│   ├── uf_robot_umi_teleop.py
│   ├── uf_robot_umi_teleop_dual.py
│   ├── calibrate.py
│   ├── config/
│   ├── rules/
│   └── xvsdk/
└── gello_teleop/             # Gello 遥操作方案
    ├── uf_robot_gello_teleop.py
    ├── config/
    └── rules/
```

## 遥操作方案

### 基于 Pika Sense 的方案

使用 Agilex Robotics 的 Pika Sense —— 一款集成 Vive Tracker 安装位的手持式夹爪控制器 —— 实时捕捉 6 自由度手部运动，并将其映射为机械臂末端执行器的运动。

- **跟踪方式**：HTC Vive Tracker + Lighthouse 基站（通过 Pika SDK）
- **控制方式**：单臂遥操作，通过夹爪开合切换启停状态
- **夹爪支持**：Pika Gripper、xArm Gripper (G1/G2)、BIO Gripper G2、Robotiq Gripper
- **运动模式**：伺服笛卡尔模式（模式 1）与在线轨迹规划模式（模式 7）

详见 [pika_teleop/README_ZH.md](pika_teleop/README_ZH.md)。

### UMI 遥操作方案

使用 FastUMI 设备实现直观的遥操作。支持单臂和双臂配置，提供灵活的跟踪选项。

- **跟踪方式**：UMI 内置 SLAM 或 HTC Vive Tracker + Lighthouse 基站（可配置切换）
- **控制方式**：单臂（`uf_robot_umi_teleop.py`）与双臂（`uf_robot_umi_teleop_dual.py`）遥操作
- **夹爪支持**：xArm Gripper G2、xArm Gripper、BIO Gripper G2、Pika Gripper、Robotiq Gripper
- **运动模式**：伺服笛卡尔模式（模式 1）与在线轨迹规划模式（模式 7）
- **双臂协作**：两个 UMI 设备通过独立线程同时控制两台 xArm 机械臂

详见 [umi_teleop/README_ZH.md](umi_teleop/README_ZH.md)。

### Gello 遥操作方案

使用 Gello 主手（基于 Dynamixel 伺服的触觉输入设备）在关节空间对 xArm 机械臂进行遥操作控制。通过串口读取 Gello 关节位置，自动计算关节偏置后映射为机器人目标关节角。

- **控制空间**：关节空间（robot_mode: 6），直接映射主手关节运动
- **支持机型**：xArm5、xArm6、xArm7（提供对应示例配置）
- **关节映射**：可通过 `joint_ids` 和 `joint_signs` 灵活配置 Gello 关节到机器人关节的映射关系
- **自动偏置**：启动时自动读取 Gello 当前姿态并计算关节偏置
- **力矩模式**：不参与映射的 Dynamixel 关节可通过 `torque_joint_ids` 开启力矩模式以保持固定
- **夹爪支持**：可选 Gello 侧 Dynamixel 夹爪，支持 xArm Gripper (G1/G2)、Pika Gripper、Robotiq Gripper

详见 [gello_teleop/README_ZH.md](gello_teleop/README_ZH.md)。


## 功能特性

- **直观操控**：直接操作界面，缩小用户与机器人本体之间的隔阂
- **经济高效**：采用成熟的商用跟踪技术与现成组件
- **高质量示教**：为模仿学习采集精准的示教数据
- **多机型兼容**：适配多种 UFACTORY 机械臂型号（xArm 5/6/7、Lite 6、850）
- **夹爪灵活可选**：支持 xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper
- **双臂协同操作**：UMI 方案支持同步双臂遥操作，适用于双手协作任务

## 快速开始

### Pika Sense 遥操作

详见 [pika_teleop/README_ZH.md](pika_teleop/README_ZH.md)。

快速启动：

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

### UMI 遥操作

详见 [umi_teleop/README_ZH.md](umi_teleop/README_ZH.md)。

快速启动（单臂）：

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

快速启动（双臂）：

```bash
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

### Gello 遥操作

详见 [gello_teleop/README_ZH.md](gello_teleop/README_ZH.md)。

快速启动：

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
# 重新登录后运行
python uf_robot_gello_teleop.py --config config/xarm7_gello_teleop.yaml
```

## 参考资料

- [Agilex Robotics Pika Sense](https://global.agilex.ai/products/pika)
- [UFACTORY 协作机械臂](https://www.ufactory.cc/xarm-collaborative-robot/)
- [LuMos FastUMI](https://www.fastumi.com/)
- [GELLO: 通用低成本遥操作框架](https://wuphilipp.github.io/gello_site/)
