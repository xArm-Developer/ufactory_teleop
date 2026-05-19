# Gello 遥操作系统

使用 Gello 主手对 UFACTORY xArm 机械臂进行关节空间遥操作控制。

GitHub: https://github.com/xArm-Developer/ufactory_teleop

本文档根据 `gello_teleop/uf_robot_gello_teleop.py` 编写，说明如何使用 Gello/Dynamixel 主手和 UFACTORY xArm 机械臂进行关节遥操作。

## 1. 简介

入口脚本通过 Dynamixel 串口读取 Gello 主手关节位置，使用 `GelloAgent` 将主手关节映射为机器人目标关节角，并统一通过 `UFRobot.send_action()` 发送给机械臂执行。

主要组件：

- `gello_teleop/uf_robot_gello_teleop.py`：Gello 遥操作入口脚本。
- `gello_teleop/config/*.yaml`：xArm5、xArm6、xArm7 示例配置文件。
- `ufactory_devices/robot/uf_robot.py`：xArm 连接、初始化、关节运动和夹爪控制封装。

支持能力：

- 支持 xArm5、xArm6、xArm7 关节空间遥操作。
- 启动时自动读取 Gello 当前姿态并计算关节偏置。
- 支持通过 `joint_ids`、`joint_signs` 配置 Gello 关节映射。
- 支持可选 Gello 夹爪关节，夹爪动作作为 action 最后一维发送。
- 支持将不参与映射的 Dynamixel 关节配置到 `torque_joint_ids` 并开启力矩模式。
- 机器人侧统一使用 `send_action` 接口，Gello 入口要求 `robot_mode: 6`。

## 2. 环境与硬件要求

推荐环境：

- Ubuntu 20.04、Ubuntu 22.04 或 Ubuntu 24.04。
- Python 3.8、3.9 或 3.10。
- UFACTORY xArm 机械臂。
- Gello 主手。
- Dynamixel USB 串口适配器。
- 可选：Gello 侧 Dynamixel 夹爪关节。
- 可选：xArm Gripper、xArm Gripper G2 或其他 `UFRobot` 支持的机器人侧夹爪。

运行前请确认：

- 控制电脑可以访问 xArm 控制器 IP。
- Gello Dynamixel 串口设备可以被当前用户访问。
- xArm 处于可使能状态，急停已释放。

## 3. 安装

克隆项目并进入 Gello 遥操作目录：

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/gello_teleop
```

创建并激活虚拟环境：

```bash
python3.9 -m venv py39
source py39/bin/activate
```

安装基础依赖：

```bash
pip install -r requirements.txt
cd src/gello
pip install -e third_party/DynamixelSDK/python
pip install -e .
```

安装后需要保证以下导入可以成功：

```bash
python -c "from gello.dynamixel.driver import DynamixelDriver; from gello.agents.gello_agent import GelloAgent"
python -c "from xarm.wrapper import XArmAPI"
```

配置串口权限：

```bash
sudo usermod -aG dialout $USER
```

执行后建议重新登录系统，或重新插拔 Gello Dynamixel USB 串口适配器。

## 4. 配置文件

示例配置文件：

```bash
gello_teleop/config/xarm7_gello_teleop.yaml
gello_teleop/config/xarm6_gello_teleop.yaml
gello_teleop/config/xarm5_gello_teleop.yaml
```

xArm7 示例：

```yaml
RobotConfig:
  robot_ip: "192.168.1.29"
  robot_mode: 6
  robot_speed: 90
  robot_acc: 500
  gripper_type: 1
  start_joints: [0, 0, 0, 1.5708, 0, 1.5708, 0]

TeleoperatorConfig:
  port: "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAJZYC7-if00-port0"
  start_joints: [0, 0, 0, 1.5708, 0, 1.5708, 0]
  gripper_id: 8
```

### RobotConfig

| 参数 | 说明 |
| --- | --- |
| `robot_ip` | 机械臂控制器 IP 地址。 |
| `robot_mode` | 机器人运动模式。Gello 入口脚本必须使用 `6`，表示关节控制模式。 |
| `robot_speed` | 关节速度，单位为 deg/s。 |
| `robot_acc` | 关节加速度，单位为 deg/s^2。 |
| `gripper_type` | 机器人侧夹爪类型。`0` 无夹爪，`1` xArm Gripper，`2` xArm Gripper G2，`10` Pika Gripper，`11` Robotiq Gripper。 |
| `gripper_port` | Pika Gripper 串口，仅 `gripper_type: 10` 时使用。 |
| `gripper_speed` | 夹爪速度，`-1` 表示使用默认值。 |
| `gripper_force` | 夹爪力控参数，`-1` 表示使用默认值。 |
| `start_joints` | 启动时机械臂先移动到的关节角，单位 rad，长度需要与机器人轴数一致。 |
| `start_tcp_pose` | 可选。到达 `start_joints` 后再移动到的 TCP 位姿，格式为 `[x, y, z, roll, pitch, yaw]`，位置单位 mm，姿态单位 rad。 |

### TeleoperatorConfig

| 参数 | 说明 |
| --- | --- |
| `fps` | 控制循环频率，默认 `30`。 |
| `port` | Gello Dynamixel 串口路径，例如 `/dev/serial/by-id/...`。 |
| `joint_ids` | 参与机器人关节映射的 Gello Dynamixel ID。xArm7 未填写时默认 `[1, 2, 3, 4, 5, 6, 7]`。 |
| `joint_signs` | 每个 Gello 关节的方向符号，长度必须与 `joint_ids` 一致。xArm7 未填写时默认全为 `1`。 |
| `start_joints` | Gello 启动参考姿态对应的机器人关节角，单位 rad，长度必须与 `joint_ids` 一致。 |
| `gripper_id` | Gello 夹爪 Dynamixel ID。设置为 `-1` 表示不使用 Gello 夹爪。 |
| `torque_joint_ids` | 需要开启力矩模式的 Dynamixel ID。常用于 xArm5/xArm6 映射中不参与控制但需要固定的 Gello 物理关节。 |

## 5. Gello 姿态对齐

脚本启动时会读取 Gello 当前关节角，并自动计算关节偏置：

```python
offset = curr_joints[i] - start_joints[i] / joint_signs[i]
```

因此，运行脚本前需要将 Gello 主手摆放到 `TeleoperatorConfig.start_joints` 对应的参考姿态。

注意事项：

- `RobotConfig.start_joints` 是机器人启动姿态。
- `TeleoperatorConfig.start_joints` 是 Gello 当前姿态对应的机器人参考关节角。
- 两者通常应保持一致，除非你明确需要一个不同的映射参考。
- 如果 Gello 未摆到参考姿态就启动，机器人接收到的目标关节角会整体偏移。
- xArm5/xArm6 示例中，部分 Gello 物理关节不参与映射，会通过 `torque_joint_ids` 固定。

## 6. 运行方法

进入 Gello 遥操作目录：

```bash
cd ufactory_teleop/gello_teleop
# xArm7
python uf_robot_gello_teleop.py --config config/xarm7_gello_teleop.yaml

# xArm6
python uf_robot_gello_teleop.py --config config/xarm6_gello_teleop.yaml

# xArm5
python uf_robot_gello_teleop.py --config config/xarm5_gello_teleop.yaml
```

## 7. 安全注意事项

- 启动脚本前确认机械臂工作空间无障碍物。
- 机械臂在显示 Enter 提示前就会连接并移动到 `RobotConfig.start_joints`。
- 首次运行建议降低 `robot_speed` 和 `robot_acc`。
- 确认 Gello 主手已摆放到 `TeleoperatorConfig.start_joints` 对应姿态后再启动脚本。
- 按 Enter 进入遥操作前，再次确认机器人和 Gello 都处于安全姿态。
- 调试时安排人员看守急停。
- 如果不使用 Gello 夹爪，请设置 `gripper_id: -1`。
- 如果不使用机器人侧夹爪，请设置 `gripper_type: 0`。
- 如果机器人返回非 0 错误码，控制循环会退出。

## 8. 常见问题

### 报错 `Gello teleop requires robot_mode=6 joint control mode`

Gello 入口脚本只支持关节控制模式。请将配置改为：

```yaml
RobotConfig:
  robot_mode: 6
```

### 报错 `joint_signs and joint_ids length mismatch`

`TeleoperatorConfig.joint_signs` 和 `TeleoperatorConfig.joint_ids` 的长度不一致。请检查两个列表的元素数量。

### 报错 `start_joints and joint_ids length mismatch`

`TeleoperatorConfig.start_joints` 和 `TeleoperatorConfig.joint_ids` 的长度不一致。请确认每个参与映射的 Gello 关节都有一个对应的参考关节角。

### 报错 `Joint action length must be ...`

`GelloAgent` 返回的 action 维度与脚本期望的 `_action_dim` 不一致。请检查 `joint_ids`、`gripper_id` 和 Gello 硬件配置。

### 无法打开 Gello 串口

请检查：

- `TeleoperatorConfig.port` 是否正确。
- USB 串口适配器是否插入。
- 当前用户是否有串口权限。
- 是否有其他进程占用了该串口。

### 按 Enter 后机器人不运动

请检查：

- xArm 控制器 IP 是否正确。
- 机器人是否处于错误或急停状态。
- UFACTORY SDK 是否可以单独控制机械臂。
- Gello 是否返回有效 action。

