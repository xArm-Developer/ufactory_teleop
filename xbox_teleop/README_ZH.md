# Xbox 手柄遥操作

使用 Xbox 兼容手柄对 UFACTORY xArm 机械臂进行笛卡尔空间控制。程序运行前或运行过程中均可连接手柄；启用遥操作前不会根据手柄输入驱动机械臂。

## 运行要求

- 一台可通过网络访问的 UFACTORY 机械臂，并已确认机器人 IP 和启动位姿配置。
- 操作系统能够识别的 Xbox 兼容手柄。
- 安装 `requirements.txt` 中列出的 Python 依赖。
- Linux 下安装了 `evdev` 时驱动优先使用 `evdev`；未安装时通过 `inputs` 读取手柄。运行程序的用户需要有权限访问手柄设备。

## 安装与启动

在仓库根目录执行：

```bash
cd xbox_teleop
pip install -r requirements.txt
```

根据目标机械臂修改 `config/xarm6_xbox_teleop.yaml`，然后启动：

```bash
python uf_robot_xbox_teleop.py --config config/xarm6_xbox_teleop.yaml
```

配置参数也可以使用简写 `-c` 传入。

## 按键说明

| 输入 | 功能 |
| --- | --- |
| 同时长按 `START` + `SELECT` 约 0.5 秒 | 启用或关闭遥操作 |
| 单独长按 `START` | 调平工具姿态 |
| 单独长按 `SELECT` | 让机械臂回到配置的 Home 位置 |
| 短按并释放 `START` | 切换默认 Z/Yaw 运动方向 |
| 方向键上 / 下 | 按下期间将 Z/Yaw 运动方向设为正向 / 负向 |
| 左摇杆（`X`、`Y` 轴） | 提供 X/Y 平移输入 |
| 右摇杆（`RX`、`RY` 轴） | 在对应旋转轴启用时控制 roll/pitch |
| 扳机（`Z`、`RZ` 轴） | 控制 Z 轴平移和 yaw |
| 面板键 `X` 或 `Y` | 启用对应的 X/Y 平移轴，并屏蔽 roll/pitch 输入 |
| 面板键 `A` 或 `B` | 启用对应的 roll/pitch 轴，并屏蔽 X/Y 平移输入 |

不按轴选择键时，可同时使用可用的平移和旋转轴。`direction` 用于旋转 XY/roll/pitch 的映射，以适配操作者的朝向。方向键左/右不会改变 Z/Yaw 的方向。

机械臂使用模式 7 接收笛卡尔目标。所有输入轴回到中立位置后，当前运动会停止；手柄断开时也会清除运动并关闭控制。重新连接后需要再次启用遥操作。

## 配置说明

`RobotConfig` 用于设置机器人连接和启动参数。至少需要将 `robot_ip` 设置为机械臂地址；运行前还应检查 `start_joints`、`start_tcp_pose` 和 `gripper_type` 是否符合实际配置。

`TeleoperatorConfig` 参数：

| 参数 | 含义 | 示例 |
| --- | --- | --- |
| `fps` | 笛卡尔指令循环频率 | `30` |
| `leveling_speed` | 调平动作使用的速度 | `45` |
| `homing_speed` | 回 Home 动作使用的速度 | `45` |
| `cartesian_speed` | 笛卡尔运动速度 | `200` |
| `direction` | XY 映射方向，可选 `0`、`90`、`180`、`270` 度 | `0` |
| `axes_deadzone` | 各轴死区，顺序为 `[X, Y, Z, RX, RY, RZ]` | `[0.15, 0.15, 0.1, 0.2, 0.2, 0.1]` |
| `max_distances` | 最大位姿偏移，顺序为 `[X, Y, Z, roll, pitch, yaw]`；平移单位为 mm，旋转单位为度 | `[500, 500, 500, 60, 60, 60]` |

示例配置中的启动位姿适用于特定 xArm6 设置，不适用于所有机械臂。连接前请确认机器人地址及与现场配置有关的参数。

## 安全须知

本软件不是安全认证的防护装置。请保持机械臂工作区域无障碍物，从较低速度和较小运动范围开始测试，并确保实体急停按钮可触及。使用回 Home 快捷键前应确认配置的 Home 位姿安全。软件启停开关不能替代急停。
