# SpaceMouse 遥操作

使用支持的 3Dconnexion SpaceMouse 对 UFACTORY xArm 机械臂进行笛卡尔空间控制。设备通过 HID 读取；运行期间驱动会持续尝试重新连接设备。

## 支持的设备

驱动目前包含以下设备配置：

| 设备 | USB 厂商 ID:产品 ID |
| --- | --- |
| SpaceNavigator | `046D:C626` |
| SpaceMouse Compact | `256F:C635` |
| SpaceMouse Wireless | `256F:C62E` |
| SpaceMouse Pro Wireless | `256F:C632` |

除表中设备外，其他型号需要在设备映射中添加对应 HID 报告格式后才能保证兼容。Pro Wireless 配置映射了多个按键，但遥操作脚本只使用前两个映射按键来启停和执行快捷操作。

## 运行要求与 HID 后端

- 一台可通过网络访问的 UFACTORY 机械臂，并已确认机器人 IP 和启动位姿配置。
- 一台受支持的 SpaceMouse。
- 安装 `requirements.txt` 中列出的 Python 依赖。

驱动根据操作系统选择后端：

- Linux 和 macOS 始终使用 HIDAPI（`hidapi`）。如果无法打开设备，Linux 可能需要调整 HID/USB 设备权限；可根据日志检查失败的设备路径和后端。
- Windows 优先使用已安装的 `pywinusb`，否则回退到 HIDAPI。`pywinusb` 是可选依赖，不包含在 `requirements.txt` 中。
- Windows 可通过 `SPACEMOUSE_BACKEND` 设置为 `pywinusb`、`hidapi` 或 `hid`。Linux/macOS 始终使用 HIDAPI，不受该变量影响。

## 安装与启动

在仓库根目录执行：

```bash
cd spacemouse_teleop
pip install -r requirements.txt
```

Windows 下可选安装 `pywinusb` 后端：

```bash
pip install pywinusb
```

根据目标机械臂修改 `config/xarm6_spacemouse_teleop.yaml`，然后启动：

```bash
python uf_robot_spacemouse_teleop.py --config config/xarm6_spacemouse_teleop.yaml
```

配置参数也可以使用简写 `-c` 传入。

## 按键与操控

| 输入 | 功能 |
| --- | --- |
| 同时长按设备映射的第一个和第二个按键约 0.5 秒 | 启用或关闭遥操作 |
| 单独长按第一个映射按键 | 调平工具姿态 |
| 单独长按第二个映射按键 | 让机械臂回到配置的 Home 位置 |
| 推、拉或倾斜控制帽 | 控制六个笛卡尔平移和旋转轴 |

SpaceNavigator、SpaceMouse Compact 和 SpaceMouse Wireless 的前两个映射按键对应左右键。Pro Wireless 配置中的前两个映射按键对应 Menu 和 Alt。Pro Wireless 的其他按键不会被遥操作脚本使用。

SpaceMouse 输入用于模式 7 下的笛卡尔目标控制。所有轴回到中立位置后，当前运动会停止；设备断开时也会清除运动并关闭控制。重新连接后需要再次启用遥操作。

## 配置说明

`RobotConfig` 用于设置机器人连接和启动参数。将 `robot_ip` 设置为机械臂地址，并根据实际设备检查启动关节、TCP 位姿和夹爪类型。

`TeleoperatorConfig` 参数：

| 参数 | 含义 | 示例 |
| --- | --- | --- |
| `fps` | 笛卡尔指令循环频率 | `30` |
| `leveling_speed` | 调平动作使用的速度 | `45` |
| `homing_speed` | 回 Home 动作使用的速度 | `45` |
| `cartesian_speed` | 笛卡尔运动速度 | `200` |
| `direction` | XY 映射方向，可选 `0`、`90`、`180`、`270` 度 | `0` |
| `axes_deadzone` | 各轴死区，顺序为 `[x, y, z, roll, pitch, yaw]` | `[0.15, 0.15, 0.10, 0.15, 0.15, 0.10]` |
| `max_distances` | 最大位姿偏移，顺序为 `[x, y, z, roll, pitch, yaw]`；平移单位为 mm，旋转单位为度 | `[500, 500, 500, 60, 60, 60]` |

示例配置中的启动位姿适用于特定 xArm6 设置，不适用于所有机械臂。连接前请确认机器人地址及与现场配置有关的参数。

## 安全须知

本软件不是安全认证的防护装置。请保持机械臂工作区域无障碍物，从较低速度和较小运动范围开始测试，并确保实体急停按钮可触及。使用回 Home 快捷键前应确认配置的 Home 位姿安全。软件启停开关不能替代急停。
