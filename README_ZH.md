# UFACTORY 遥操作系统

本项目为 UFACTORY（深圳市众为创造科技有限公司）机械臂提供遥操作解决方案，通过运动跟踪实现对机械臂的直观远程控制，降低高质量示教数据采集的门槛，服务于机器人学习和操作任务。适配 xArm 5/6/7、Lite 6、850，五套方案共用可安装的核心库 `uf_teleop_core`（[src/uf_teleop_core](src/uf_teleop_core/README_ZH.md)）。

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

## 配置单位

仓库示例配置在顶层声明 `angle_unit: deg`。所有连续角度量都跟随该单位：姿态角（`start_joints`、`start_tcp_pose` 姿态、`tracker_to_robot_eef`、`robot_base_pose`）、关节模式下的 `robot_speed` / `robot_acc`、`max_distances` 的旋转分量，以及 `leveling_speed` / `homing_speed`。`load_config()` 会把它们转换为内部使用的单位。

例外：`direction`（`0/90/180/270`）和笛卡尔模式的 `robot_speed` / `robot_acc`（mm/s、mm/s²）不跟随 `angle_unit`。录制的 `TeleopData.delta` 始终为 mm/deg。缺少 `angle_unit` 的配置保持旧的混合单位（姿态为弧度，上述其余字段为度）并给出警告。

## 1. Pika Sense 遥操作

使用 Agilex Robotics 的 Pika Sense —— 一款集成 Vive Tracker 安装位的手持式夹爪控制器 —— 实时捕捉 6 自由度手部运动，并将其映射为机械臂末端执行器的运动。

[![观看视频](https://i0.hdslb.com/bfs/archive/df77a7fb494a674bc01168b0d865ba04aac12228.jpg)](https://www.bilibili.com/video/BV1791rB4Egk/?spm_id_from=333.1387)

- **跟踪方式**：HTC Vive Tracker + Lighthouse 基站（通过 Pika SDK）
- **控制方式**：单臂遥操作，通过夹爪开合切换启停状态
- **夹爪支持**：xArm Gripper (G1/G2)、BIO Gripper G2、Pika Gripper、Robotiq Gripper
- **运动模式**：伺服笛卡尔模式（模式 1）与在线轨迹规划模式（模式 7）

```bash
# 以下命令在仓库根目录执行
conda create --name py39 python=3.9
conda activate py39
pip install -e ".[pika]"
# Pika SDK（跳过其 GUI/相机专用依赖）：
pip install pysurvive agx-pypika --no-deps
# 可选完整 Pika/Vive SDK（会拉取 GUI/相机依赖）：
# pip install -e ".[pika,vive]"
sudo cp pika_teleop/rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

cd pika_teleop
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
# 以下命令在仓库根目录执行
conda create --name py39 python=3.9
conda activate py39
sudo dpkg -i umi_teleop/xvsdk/XVSDK_focal_amd64.deb
sudo apt install -y --fix-broken
pip install -e ".[umi]"
# Vive Tracker / Pika Gripper SDK（跳过其 GUI/相机专用依赖）：
pip install pysurvive agx-pypika --no-deps
# 可选完整 Vive/Pika SDK（会拉取 GUI/相机依赖）：
# pip install -e ".[umi,vive]"
sudo cp umi_teleop/rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

cd umi_teleop
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
# 以下命令在仓库根目录执行
conda create --name py39 python=3.9
conda activate py39
pip install -e ".[gello]"
sudo usermod -aG dialout $USER
# 重新登录后运行
cd gello_teleop
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
# 以下命令在仓库根目录执行
pip install -e ".[xbox]"

cd xbox_teleop
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
# 以下命令在仓库根目录执行
pip install -e ".[spacemouse]"

cd spacemouse_teleop
# 根据机械臂修改 config/xarm6_spacemouse_teleop.yaml
python uf_robot_spacemouse_teleop.py --config config/xarm6_spacemouse_teleop.yaml
```

按键说明与配置参数见 [spacemouse_teleop/README_ZH.md](spacemouse_teleop/README_ZH.md)。

## 设备独立使用与数据采集

遥操作设备（`TeleopDevice`）与机器人设备（`RobotDevice`）可各自独立使用，入口脚本只负责组合二者。先执行 `pip install -e .` 安装核心库，完整接口见 [src/uf_teleop_core/README_ZH.md](src/uf_teleop_core/README_ZH.md)。

```python
from uf_teleop_core.teleop import PikaTeleopDevice

with PikaTeleopDevice(use_gripper=True) as device:
    data = device.get_data()
    if data is not None and data.valid:
        print(data.position, data.quaternion, data.gripper, data.buttons)
```

独立采集遥操作数据（v2 JSONL 格式）：

```bash
# 仅采集 teleop 设备
python scripts/collect_data.py --teleop-type pika \
    -c pika_teleop/config/xarm6_pika_teleop.yaml -o data/pika_ep001.jsonl

# 同时记录机械臂状态（初始化会移动机械臂到 start_joints，采集中不发送动作）
python scripts/collect_data.py --teleop-type umi \
    -c umi_teleop/config/xarm6_umi_teleop.yaml -o data/umi_ep001.jsonl --with-robot
```

支持 `--teleop-type pika|umi|gello|xbox|spacemouse`；`Ctrl+C` 结束采集。`--with-robot` 会按同一 YAML 的 `RobotConfig` 连接机械臂。

使用 Pika 或 UMI 设备采集时，还需按对应方案快速开始中的说明安装设备 SDK（`pip install pysurvive agx-pypika --no-deps`）。

录制文件使用 v2 格式：首行是 meta（`teleop_type`、`space`、`fps`、`t0_us` 与单位），之后每行一帧，时间用相对 `t_us`。`space` 只在文件头记录一次；默认跳过无效帧（`--keep-invalid` 保留稀疏标记），原始轴值默认不记录（`--include-axes` 开启），输出路径以 `.gz` 结尾时自动 gzip 压缩。回放仅支持 v2 文件；旧版本生成的文件需要重新采集。

回放采集的遥操作数据到机械臂（`--dry-run` 只计算动作，不连接机器人）：

```bash
# 预览
python scripts/replay_data.py -i data/pika_ep001.jsonl \
    -c pika_teleop/config/xarm6_pika_teleop.yaml --dry-run

# 半速回放
python scripts/replay_data.py -i data/pika_ep001.jsonl \
    -c pika_teleop/config/xarm6_pika_teleop.yaml --speed 0.5
```

支持 `cartesian`（pika/umi）、`joint`（gello）、`cartesian_delta`（xbox/spacemouse）。Xbox 数据会重放方向键的 Z/YAW 符号，但单击 START 的 Z/YAW 反转开关未被记录。不传 `--fps` 时使用录制时间戳，传入则按固定帧率回放。

## 参考资料

- [Agilex Robotics Pika Sense](https://global.agilex.ai/products/pika)
- [UFACTORY 协作机械臂](https://www.ufactory.cc/xarm-collaborative-robot/)
- [LuMos FastUMI](https://www.fastumi.com/)
- [GELLO: 通用低成本遥操作框架](https://wuphilipp.github.io/gello_site/)
- [Xbox 360 手柄](https://www.xbox.com/en-US/accessories)
- [3Dconnexion 无线鼠标](https://3dconnexion.com/cn/product/spacemouse-wireless/)
