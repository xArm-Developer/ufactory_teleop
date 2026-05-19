# Pika 遥操作系统


使用松灵机器人的Pika Sense (https://global.agilex.ai/products/pika)   
对 UFACTORY(深圳市众为创造科技有限公司) 的机械臂(https://www.ufactory.cc/xarm-collaborative-robot/) 进行遥操作控制。  

GitHub: https://github.com/xArm-Developer/ufactory_teleop

[![Watch the video](../assets/pika_teleoperation_system.jpg)](https://www.bilibili.com/video/BV1791rB4Egk/?spm_id_from=333.1387.homepage.video_card.click&vd_source=9cdbfdb03a35ac858f97ba3ca89dc358)


本文档根据 `pika_teleop/uf_robot_pika_teleop.py` 编写，说明如何使用 Pika Sense、Vive Tracker 和 UFACTORY xArm 机械臂进行笛卡尔空间遥操作。

## 1. 简介

入口脚本通过 Pika Sense 获取 Vive Tracker 位姿，将手柄运动转换为机械臂末端目标位姿，并通过 `UFRobot` 发送给机械臂执行。

主要组件：

- `pika_teleop/uf_robot_pika_teleop.py`：Pika Sense 遥操作入口脚本。
- `ufactory_devices/pika/pika_device.py`：Pika Sense 和 Pika Gripper 串口自动识别与连接。
- `ufactory_devices/robot/uf_robot.py`：xArm 连接、初始化、运动和夹爪控制封装。
- `ufactory_devices/transformations.py`：位姿、四元数、RPY、轴角和相对运动转换。

支持能力：

- Pika Sense 串口自动识别。
- 通过 Pika SDK 获取 Vive Tracker 位姿。
- 通过 Pika Sense command state 控制遥操作开始和停止。
- 可选读取 Pika Sense 夹爪距离并控制机器人夹爪。
- 默认使用 xArm `robot_mode: 7`，发送轴角形式的笛卡尔目标位姿。

## 2. 环境与硬件要求

推荐环境：

- Ubuntu 22.04 或 Ubuntu 24.04。
- Python 3.8、3.9 或 3.10。
- UFACTORY xArm 机械臂。
- Pika Sense。
- Vive Tracker 和 Lighthouse 基站。
- 可选：Pika Gripper 或其他支持的 xArm 夹爪。

## 3. 安装

克隆项目并进入 Pika 遥操作目录：

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/pika_teleop
```

创建并激活虚拟环境：

```bash
python3.9 -m venv py39
source py39/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
pip install pysurvive
```

配置 USB、串口和 Vive 设备规则：

```bash
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

执行后建议重新插拔 Pika Sense、Vive Tracker 和 Pika Gripper。

## 4. 配置文件

示例配置文件：

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

| 参数 | 说明 |
| --- | --- |
| `robot_ip` | 机械臂控制器 IP 地址。 |
| `robot_mode` | 运动模式。`1` 为 servo 笛卡尔伺服模式，`7` 为笛卡尔在线轨迹规划模式，默认 `7`。 |
| `robot_speed` | 机械臂运动速度，默认 `250`。 |
| `robot_acc` | 机械臂运动加速度，默认 `1000`。 |
| `gripper_type` | 夹爪类型。`0` 无夹爪，`1` xArm Gripper，`2` xArm Gripper G2，`3` BIO Gripper G2，`10` Pika Gripper，`11` Robotiq Gripper。 |
| `gripper_port` | Pika Gripper 串口，仅 `gripper_type: 10` 时使用。不填时程序尝试自动识别。 |
| `gripper_speed` | 夹爪速度，`-1` 表示使用默认值。 |
| `gripper_force` | 夹爪力控参数，`-1` 表示使用默认值。 |
| `start_joints` | 启动时机械臂先移动到的关节角，单位 rad。 |
| `start_tcp_pose` | 可选。到达 `start_joints` 后再移动到的 TCP 位姿，格式为 `[x, y, z, roll, pitch, yaw]`，位置单位 mm，姿态单位 rad。 |

### TeleoperatorConfig

| 参数 | 说明 |
| --- | --- |
| `fps` | 控制循环频率，默认 `30`。 |
| `use_gripper` | 是否读取 Pika Sense 夹爪距离并向机器人发送夹爪目标。 |
| `pika_sense_port` | Pika Sense 串口，例如 `/dev/ttyUSB0`。不填时 `PikaDevice` 会扫描 VID/PID 为 `1a86:7522` 的串口设备。 |
| `vive_tracker_id` | `pika_sense.get_pose()` 使用的 Vive Tracker 设备名字，默认 `WM0`。|
| `tracker_to_robot_eef` | Tracker/Pika 坐标系到机器人末端坐标系的变换，格式为 `[x, y, z, roll, pitch, yaw]`。 |

## 5. Vive Tracker 标定

首次使用或 Lighthouse 基站位置变化后，运行：

```bash
cd ufactory_teleop/pika_teleop
python calibrate.py
```

标定脚本会删除 `~/.config/libsurvive/config.json`，使用 `pysurvive` 强制重新标定，并持续输出检测到的 tracker 位姿。标定过程中不要移动基站和 tracker。

## 6. 运行方法

进入 Pika 遥操作目录：

```bash
cd ufactory_teleop/pika_teleop
python uf_robot_pika_teleop.py --config config/xarm6_pika_teleop.yaml
```

启动流程：

1. 读取 YAML 配置。
2. 连接机械臂。
3. 机械臂移动到 `start_joints`，再可选移动到 `start_tcp_pose`。
4. 连接 Pika Sense 并初始化 Vive Tracker。
5. 显示 `Enter to control robot with teleop >>>`。
6. 按 Enter 后进入控制循环。

脚本通过 Pika Sense command state 的变化控制遥操作开始和停止。通常快速张开/闭合 Pika Sense 夹子即可触发 command state 变化。


## 7. 安全注意事项

- 启动脚本前确认机械臂工作空间无障碍物。
- 机械臂在遥操作开始前的初始化阶段就会运动。
- 先低速验证 `start_joints` 和 `start_tcp_pose` 是否安全。
- 调试时安排人员看守急停。
- 首次运行建议降低 `robot_speed` 和 `robot_acc`。
- 触发开始控制时保持 Pika Sense 稳定，因为第一帧位姿会作为遥操作参考点。

