# UMI 遥操作使用文档

使用 LUMOS(鹿明机器人科技有限公司) 的FastUMI (https://lumosumi.lumosbot.tech/pro/)   
对 UFACTORY(深圳市众为创造科技有限公司) 的机械臂(https://www.ufactory.cc/xarm-collaborative-robot/) 进行遥操作控制。  

GitHub: https://github.com/xArm-Developer/ufactory_teleop

本文档根据 `umi_teleop/uf_robot_umi_teleop.py` 和 `umi_teleop/uf_robot_umi_teleop_dual.py` 编写，说明如何使用 UMI 设备遥操作一台或两台 UFACTORY xArm 机械臂。

## 1. 简介

UMI 遥操作脚本读取 UMI SLAM 位姿或 Vive Tracker 位姿，将手部相对运动转换为机械臂末端目标位姿，并通过 `UFRobot` 发送给机械臂。

入口脚本：

- `umi_teleop/uf_robot_umi_teleop.py`：单个 UMI 设备控制单台机械臂。
- `umi_teleop/uf_robot_umi_teleop_dual.py`：两个 UMI 设备控制两台机械臂，内部使用两个后台线程运行。

支持的位姿来源：

- `use_vive_tracker: True`：使用 Vive Tracker 位姿。
- `use_vive_tracker: False`：直接使用 UMI SLAM 位姿。

## 2. 环境与硬件要求

推荐环境：

- Ubuntu 22.04 或 Ubuntu 24.04。
- Python 3.8、3.9 或 3.10。
- UFACTORY xArm 机械臂。
- FAST UMI / UMI 设备。
- 可选：Vive Tracker 和 Lighthouse 基站。
- 可选：受支持的机械臂夹爪。

## 3. 安装

克隆项目并进入 UMI 遥操作目录：

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/umi_teleop
```

创建并激活虚拟环境：

```bash
conda create --name py39 python=3.9
conda activate py39
```

安装 XVSDK：

```bash
sudo dpkg -i xvsdk/XVSDK_focal_amd64.deb
sudo apt install -y --fix-broken
```

安装 Python 依赖：

```bash
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
```

安装后需要保证以下导入可以成功：

```bash
python -c "import cv2;import pysurvive;from pika.gripper import Gripper;from xarm.wrapper import XArmAPI"
```

配置 USB 规则：

```bash
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

执行后建议重新插拔 UMI 和 Vive 设备。

如果需要同时使用多个 UMI 设备，可增大 USB buffer：

```bash
sudo sed -i '/GRUB_CMDLINE_LINUX_DEFAULT/s/quiet splash/quiet splash usbcore.usbfs_memory_mb=128/' /etc/default/grub
sync
sudo update-grub
sudo reboot
```

## 4. 配置文件

示例文件：

- 单臂：`umi_teleop/config/xarm6_umi_teleop.yaml`
- 双臂：`umi_teleop/config/xarm6_umi_teleop_dual.yaml`

### 单臂配置

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

### 双臂配置

双臂脚本要求最外层包含 `L` 和 `R`，每组内部都有自己的 `RobotConfig` 和 `TeleoperatorConfig`。

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

## 5. 参数说明

### RobotConfig

| 参数 | 说明 |
| --- | --- |
| `robot_ip` | 机械臂控制器 IP 地址。 |
| `robot_mode` | 运动模式。`1` 为 servo 笛卡尔伺服模式，`7` 为笛卡尔在线轨迹规划模式，默认 `7`。 |
| `robot_speed` | 机械臂运动速度，默认 `250`。 |
| `robot_acc` | 机械臂运动加速度，默认 `1000`。 |
| `gripper_type` | `0` 无夹爪，`1` xArm Gripper，`2` xArm Gripper G2，`10` Pika Gripper，`11` Robotiq Gripper。 |
| `gripper_port` | Pika Gripper 串口，仅 `gripper_type: 10` 时使用，不指定则自动检测。 |
| `gripper_speed` | 夹爪速度，`-1` 表示使用默认值。 |
| `gripper_force` | 夹爪力控参数，`-1` 表示使用默认值。 |
| `start_joints` | 启动时机械臂先移动到的关节角，单位 rad。 |
| `start_tcp_pose` | 可选启动 TCP 位姿，格式为 `[x, y, z, roll, pitch, yaw]`，位置单位 mm，姿态单位 rad。 |

### TeleoperatorConfig

| 参数 | 说明 |
| --- | --- |
| `serial_number` | UMI 设备序列号，必填。 |
| `fps` | 控制循环频率，默认 `30`。 |
| `use_gripper` | 是否读取 UMI clamp stream 并追加夹爪控制量。 |
| `use_vive_tracker` | 是否使用 Vive Tracker 位姿。为 `False` 时使用 UMI SLAM 位姿。 |
| `vive_tracker_id` | Vive Tracker ID，例如 `LHR-555DC7BF`，双臂时请一定要使用序列号而不是"WM0"这种设备名。 |
| `tracker_to_robot_eef` | Tracker/UMI 坐标系到机器人末端坐标系的变换。 |
| `robot_base_pose` | 遥操作基准机械臂末端位姿。 |

## 6. Vive Tracker 标定

首次使用或 Lighthouse 基站位置变化后，运行：

```bash
cd ufactory_teleop/umi_teleop
python calibrate.py
```

脚本会删除 `~/.config/libsurvive/config.json`，强制重新标定，并持续输出检测到的 tracker 位姿。标定过程中不要移动基站和 tracker。

## 7. 运行方法

单臂：

```bash
cd ufactory_teleop/umi_teleop
python uf_robot_umi_teleop.py --config config/xarm6_umi_teleop.yaml
```

双臂：

```bash
cd ufactory_teleop/umi_teleop
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

启动流程：

1. 读取 YAML 配置。
2. 连接并初始化一台或两台机械臂。
3. 每台机械臂移动到 `start_joints`，再可选移动到 `start_tcp_pose`。
4. 初始化 UMI 和可选 Vive Tracker。
5. 显示 `Enter to control robot with teleop >>>`。
6. 按 Enter 后开始遥操作。

## 8. 安全注意事项

- 机械臂在遥操作开始前的初始化阶段就会运动。
- 先低速验证 `start_joints`、`start_tcp_pose` 和 `robot_base_pose` 是否安全。
- 保持工作空间无障碍物，并安排人员看守急停。
- 双臂运行前逐项确认左右机械臂的 `robot_ip`、`serial_number`、`vive_tracker_id` 和 `tracker_to_robot_eef` 没有填反。

