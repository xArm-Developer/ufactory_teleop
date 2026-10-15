# UFACTORY 遥操作系统

本项目为 UFACTORY（深圳市众为创造科技有限公司）机械臂提供遥操作解决方案，通过运动跟踪实现对机械臂的直观远程控制，降低高质量示教数据采集的门槛，服务于机器人学习和操作任务。适配 xArm 5/6/7、Lite 6、850，五套方案共用 [ufactory_devices/](ufactory_devices/README_ZH.md) 中的机械臂封装与设备驱动。

[English](README.md) | [Pika](#1-pika-sense-遥操作) | [UMI](#2-umi-遥操作) | [Gello](#3-gello-遥操作) | [Xbox](#4-xbox-手柄遥操作) | [SpaceMouse](#5-spacemouse-遥操作)

共提供五套独立方案：

| 方案 | 输入设备 | 控制空间 | 外部定位 | 末端执行器 |
| --- | --- | --- | --- | --- |
| [Pika Sense 遥操作](pika_teleop/README_ZH.md) | Pika Sense 手持夹爪 | 笛卡尔 | 需要：Vive Tracker + Lighthouse 基站 | xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper |
| [UMI 遥操作](umi_teleop/README_ZH.md) | FastUMI | 笛卡尔（单臂/双臂） | 可选：UMI 内置 SLAM 或 Vive Tracker | xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper |
| [Gello 遥操作](gello_teleop/README_ZH.md) | Gello 主手（Dynamixel 伺服） | 关节 | 不需要 | xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper（另有 Gello 侧 Dynamixel 夹爪） |
| [Xbox 手柄遥操作](xbox_teleop/README_ZH.md) | Xbox 兼容手柄 | 笛卡尔 | 不需要 | 不控制夹爪 |
| [SpaceMouse 遥操作](spacemouse_teleop/README_ZH.md) | 3Dconnexion SpaceMouse | 笛卡尔 | 不需要 | 不控制夹爪 |

## 获取代码

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop
```

以下各方案的命令均从仓库根目录开始执行。

## 1. Pika Sense 遥操作

使用 Agilex Robotics 的 Pika Sense —— 一款集成 Vive Tracker 安装位的手持式夹爪控制器 —— 实时捕捉 6 自由度手部运动，并将其映射为机械臂末端执行器的运动。

[![观看视频](https://i0.hdslb.com/bfs/archive/df77a7fb494a674bc01168b0d865ba04aac12228.jpg)](https://www.bilibili.com/video/BV1791rB4Egk/?spm_id_from=333.1387)

- **跟踪方式**：HTC Vive Tracker + Lighthouse 基站（通过 Pika SDK）
- **控制方式**：单臂遥操作，通过夹爪开合切换启停状态
- **夹爪支持**：xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper
- **运动模式**：伺服笛卡尔模式（模式 1）与在线轨迹规划模式（模式 7）

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

标定流程、配置参数与排错见 [pika_teleop/README_ZH.md](pika_teleop/README_ZH.md)。

## 2. UMI 遥操作

使用 FastUMI 设备实现直观的遥操作，支持单臂和双臂配置，并提供灵活的跟踪选项。

[![观看视频](https://i0.hdslb.com/bfs/archive/5a0c22cc1a325b4c48d25413def2ba84dbfeca87.jpg)](https://www.bilibili.com/video/BV1qAGm6fEZE/?spm_id_from=333.1387)

- **跟踪方式**：UMI 内置 SLAM 或 HTC Vive Tracker + Lighthouse 基站（可配置切换）
- **控制方式**：单臂（`uf_robot_umi_teleop.py`）与双臂（`uf_robot_umi_teleop_dual.py`）遥操作
- **夹爪支持**：xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper
- **运动模式**：伺服笛卡尔模式（模式 1）与在线轨迹规划模式（模式 7）
- **双臂协作**：两个 UMI 设备通过独立线程同时控制两台 xArm 机械臂

单臂：

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

双臂（完成上述安装后）：

```bash
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

标定流程、配置参数与排错见 [umi_teleop/README_ZH.md](umi_teleop/README_ZH.md)。

## 3. Gello 遥操作

使用 Gello 主手（基于 Dynamixel 伺服的触觉输入设备）在关节空间对 xArm 机械臂进行遥操作控制。通过串口读取 Gello 关节位置，自动计算关节偏置后映射为机器人目标关节角。

[![观看视频](https://i2.hdslb.com/bfs/archive/7b325df5fb4c16e922b66d27b56d8fb6534f8b46.jpg)](https://www.bilibili.com/video/BV12xFjzzEaX/?spm_id_from=333.1387)

- **控制空间**：关节空间（robot_mode: 6），直接映射主手关节运动
- **支持机型**：xArm5、xArm6、xArm7（提供对应示例配置）
- **关节映射**：可通过 `joint_ids` 和 `joint_signs` 灵活配置 Gello 关节到机器人关节的映射关系
- **自动偏置**：启动时自动读取 Gello 当前姿态并计算关节偏置
- **力矩模式**：不参与映射的 Dynamixel 关节可通过 `torque_joint_ids` 开启力矩模式以保持固定
- **夹爪支持**：可选 Gello 侧 Dynamixel 夹爪，支持 xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper

```bash
cd gello_teleop
conda create --name py39 python=3.9
conda activate py39
pip install -r requirements.txt
sudo usermod -aG dialout $USER
# 重新登录后运行
python uf_robot_gello_teleop.py --config config/xarm7_gello_teleop.yaml
```

运行前需将 Gello 主手摆放到配置中 `TeleoperatorConfig.start_joints` 对应的参考姿态。姿态对齐、配置参数与排错见 [gello_teleop/README_ZH.md](gello_teleop/README_ZH.md)。

## 4. Xbox 手柄遥操作

使用 Xbox 兼容手柄对机械臂末端执行器进行六轴笛卡尔控制。手柄驱动支持 Linux（安装 `evdev` 时优先使用该后端），以及 `inputs` 支持的平台。

[![观看视频](https://i0.hdslb.com/bfs/archive/17e3de5b320b33bd44f99b23ddb4f2e6aa8dc6f5.jpg)](https://www.bilibili.com/video/BV1Y2JC6bEgh/)

- **启停控制**：同时长按 `START` + `SELECT` 约 0.5 秒，切换控制的启用或关闭
- **运动控制**：使用摇杆和扳机控制笛卡尔平移与旋转；方向键可调整 Z 轴/Yaw 的运动方向
- **轴选择**：`X`/`Y` 选择平移轴，`A`/`B` 选择旋转轴
- **快捷操作**：长按 `START` 调平工具姿态，长按 `SELECT` 让机械臂回到 Home 位置；短按 `START` 可反转 Z 轴/Yaw 的方向

```bash
cd xbox_teleop
pip install -r requirements.txt
# 根据机械臂修改 config/xarm6_xbox_teleop.yaml
python uf_robot_xbox_teleop.py --config config/xarm6_xbox_teleop.yaml
```

按键说明与配置参数见 [xbox_teleop/README_ZH.md](xbox_teleop/README_ZH.md)。

## 5. 六维 SpaceMouse 遥操作

使用支持的 3Dconnexion SpaceMouse 作为六自由度输入设备，对机械臂末端执行器进行笛卡尔控制。

[![观看视频](https://i1.hdslb.com/bfs/archive/3119523db01a4aab792c84100879e9eaab8ed4e4.jpg)](https://www.bilibili.com/video/BV168JC6gE1e/)

- **启停控制**：同时长按设备左右两个按键约 0.5 秒，切换控制的启用或关闭
- **快捷操作**：长按左键调平工具姿态，长按右键让机械臂回到 Home 位置
- **HID 后端**：Linux 和 macOS 使用 HIDAPI。Windows 优先使用已安装的 `pywinusb`，否则回退到 HIDAPI；也可通过 `SPACEMOUSE_BACKEND` 指定 Windows 后端

```bash
cd spacemouse_teleop
pip install -r requirements.txt
# 根据机械臂修改 config/xarm6_spacemouse_teleop.yaml
python uf_robot_spacemouse_teleop.py --config config/xarm6_spacemouse_teleop.yaml
```

按键说明与配置参数见 [spacemouse_teleop/README_ZH.md](spacemouse_teleop/README_ZH.md)。

## 参考资料

- [Agilex Robotics Pika Sense](https://global.agilex.ai/products/pika)
- [UFACTORY 协作机械臂](https://www.ufactory.cc/xarm-collaborative-robot/)
- [LuMos FastUMI](https://www.fastumi.com/)
- [GELLO: 通用低成本遥操作框架](https://wuphilipp.github.io/gello_site/)
- [Xbox 360 手柄](https://www.xbox.com/en-US/accessories)
- [3Dconnexion 无线鼠标](https://3dconnexion.com/cn/product/spacemouse-wireless/)
