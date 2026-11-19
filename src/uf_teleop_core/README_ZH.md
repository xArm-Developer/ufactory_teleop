# uf_teleop_core

五套遥操作方案共享的可安装核心库。各方案自己的脚本只负责「读取输入 → 计算映射 → 下发动作」的循环，所有与硬件打交道的代码集中在这里：xArm 机械臂封装、输入设备驱动，以及统一的 teleop / robot 设备接口。

## 安装

在仓库根目录执行：

```bash
pip install -e .                          # 仅核心依赖（numpy、PyYAML）
pip install -e ".[pika]"                  # + xArm SDK + Pika 串口依赖（Pika SDK 见下方）
pip install -e ".[umi]"                   # + xArm SDK + UMI 相机依赖（Vive SDK 见下方）
pip install -e ".[gello]"                 # + Gello（Dynamixel）SDK
pip install -e ".[xbox]"                  # + Xbox 兼容手柄
pip install -e ".[spacemouse]"            # + 3Dconnexion SpaceMouse
pip install -e ".[robot]"                 # + xArm Python SDK
pip install -e ".[vive]"                  # + 完整 pysurvive/agx-pypika SDK（较重）
pip install -e ".[dev]"                   # + pytest
pip install -e ".[all]"                   # 上述全部（不含 [vive]）
```

系统级依赖（Vive/Lighthouse 的 `pysurvive`、XVSDK deb、udev 规则）仍按根 README 中各方案的说明安装。

`pysurvive` 与 `agx-pypika` 需要单独用 `--no-deps` 安装：它们的元数据会拉取遥操作路径用不到的 GUI/相机依赖（`gooey`、`wxpython`、`pyrealsense2`）：

```bash
pip install pysurvive agx-pypika --no-deps
```

如需声明式的完整 SDK 安装（包含 Pika 相机/GUI 工具），使用 `pip install -e ".[pika,vive]"`。正常安装会拉取上述 GUI/相机依赖；`--no-deps` 不能与 extras 组合使用，因为它会连 extra 依赖一并跳过。

## 目录结构

```
src/uf_teleop_core/
├── transformations.py          # Transformations：位姿数学工具
├── devices/
│   ├── pika/
│   │   └── pika_device.py      # PikaDevice：Pika Sense / Pika Gripper 串口驱动
│   ├── umi/
│   │   ├── xvlib/              # XVLib：libxvlib.so 的 ctypes 封装（含 .so 兜底库）
│   │   └── vive_tracker/       # ViveTracker：基于 pysurvive 的 Tracker 驱动
│   ├── xbox/
│   │   └── xbox_device.py      # XBoxDevice：Xbox 兼容手柄驱动
│   ├── spacemouse/
│   │   └── space_device.py     # SpaceDevice：3Dconnexion SpaceMouse 驱动
│   └── gello/
│       └── gello_device.py     # GelloDevice：Dynamixel + GelloAgent 封装与标定
├── teleop/
│   ├── base.py                 # TeleopData / TeleopDevice：遥操作设备接口
│   ├── mapping.py              # CartesianTeleopMapper：遥操作位姿 -> 机器人目标位姿
│   ├── pika_teleop_device.py   # PikaTeleopDevice
│   ├── umi_teleop_device.py    # UmiTeleopDevice
│   ├── gello_teleop_device.py  # GelloTeleopDevice
│   ├── xbox_teleop_device.py   # XboxTeleopDevice（增量型）
│   └── spacemouse_teleop_device.py # SpacemouseTeleopDevice（增量型）
└── robot/
    ├── base.py                 # RobotDevice / RobotState：机器人设备接口
    └── uf_robot.py             # UFRobot：xArm 连接、运动、夹爪控制
```

请按子包显式导入，例如 `from uf_teleop_core.robot import UFRobot` 或 `from uf_teleop_core.devices.pika import PikaDevice`。

## 各方案使用的模块

| 遥操作方案 | 从 uf_teleop_core 引入 |
| --- | --- |
| [pika_teleop](../../pika_teleop/README_ZH.md) | `teleop.PikaTeleopDevice`、`teleop.CartesianTeleopMapper`、`robot.UFRobot` |
| [umi_teleop](../../umi_teleop/README_ZH.md) | `teleop.UmiTeleopDevice`、`teleop.CartesianTeleopMapper`、`robot.UFRobot` |
| [gello_teleop](../../gello_teleop/README_ZH.md) | `teleop.GelloTeleopDevice`、`robot.UFRobot` |
| [xbox_teleop](../../xbox_teleop/README_ZH.md) | `teleop.XboxTeleopDevice`、`robot.UFRobot` |
| [spacemouse_teleop](../../spacemouse_teleop/README_ZH.md) | `teleop.SpacemouseTeleopDevice`、`robot.UFRobot` |

## robot/ —— xArm 机械臂封装

`from uf_teleop_core.robot import UFRobotConfig, UFRobot`

### UFRobotConfig

| 字段 | 说明 |
| --- | --- |
| `robot_ip` | xArm 控制器 IP 地址。 |
| `robot_mode` | 运动模式。`1` 伺服笛卡尔、`6` 关节控制、`7`（默认）在线轨迹规划。 |
| `robot_speed` / `robot_acc` | 运动速度与加速度。 |
| `gripper_type` | 夹爪类型，取值见 `GripperType`。 |
| `gripper_port` | 夹爪串口，仅 Pika Gripper (`10`) 使用。 |
| `gripper_speed` / `gripper_force` | `-1` 表示使用各夹爪的默认值。 |
| `start_joints` | 启动时先移动到的关节角，单位 rad。 |
| `start_tcp_pose` | 可选。到达 `start_joints` 后再移动到的 TCP 位姿 `[x, y, z, roll, pitch, yaw]`。 |

`GripperType` 取值：`NoGripper=0`、`xArmGripper=1`、`xArmGripperG2=2`、`BioGripperG2=3`、`PikaGripper=10`、`RobotiqGripper=11`。

### UFRobot

`UFRobot(config)` —— 构造时即连接控制器、使能电机、清除错误，并运动到 `start_joints`。**实例化就会驱动机械臂**，务必先确认工作空间。

- `send_action(action)` —— 各方案统一的下发接口，按 `robot_mode` 分派：
  - `robot_mode: 6`：`action[:轴数]` 为关节角（rad），`action[轴数]` 为夹爪归一化值（0 张开 → 1 闭合）。
  - `robot_mode: 7` 与其他：`action[:6]` 为 `[x, y, z, rx, ry, rz]`，`action[6]` 为夹爪归一化值。
  - 夹爪按类型分别走 TDK Modbus（xArm Gripper G1/G2、BIO Gripper G2、Robotiq）或串口（Pika Gripper）。
  - 返回控制器错误码，调用方应在循环中检查，非 0 时退出。
- `get_position(is_axis_angle=False)` —— 读取当前位姿（默认 xyzrpy，可选轴角）。
- `get_state()` —— 读取 `RobotState` 快照：`tcp_pose`（xyzrpy，mm/rad）、`joints`（rad）、`gripper_norm`（最近一次下发值）、`error_code`。
- `robot_init(enable=True, init_gripper_pose=False)` —— 重置模式与状态，并按需初始化夹爪。
- `close()` —— 断开机械臂（以及使用中的 Pika 夹爪）。
- `action_space` / `connected` —— `RobotActionSpace.CARTESIAN` 或 `JOINT`，以及连接状态。

`UFRobot` 实现了 `robot/base.py` 中的 `RobotDevice` 接口（`connect`、`close`、`get_state`、`send_action`、`action_space`），可替换为其他机器人后端；`RobotState`、`RobotActionSpace` 从 `uf_teleop_core.robot` 导出。

## teleop/ —— 遥操作设备层

`from uf_teleop_core.teleop import TeleopData, TeleopDevice, CartesianTeleopMapper`

遥操作设备只负责取数，不感知机器人。`get_data()` 返回最新一帧 `TeleopData`，无可用数据时返回 `None`：

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 单调时钟秒数。 |
| `space` | `cartesian`、`cartesian_delta` 或 `joint`。 |
| `position` | `[x, y, z]`，单位米，设备坐标系。 |
| `quaternion` | 姿态四元数 `[x, y, z, w]`（xyzw）。 |
| `joints` | 关节角（rad，Gello）。 |
| `gripper` | 归一化 `0` 张开 → `1` 闭合，可直接作为 `UFRobot.send_action` 的最后一位。 |
| `buttons` | 设备状态，例如 Pika 的 `{"command": 0/1}`、Xbox 的 `{"START": 0/1, ...}`。 |
| `delta` | `[dx, dy, dz, drx, dry, drz]`，mm/rad，rpy 增量（增量型设备）。 |
| `axes` | 原始轴值（增量型设备），用于零输入判断与数据采集。 |

设备与机器人解耦，可独立使用：

```python
from uf_teleop_core.teleop import PikaTeleopDevice

with PikaTeleopDevice(use_gripper=True) as device:
    data = device.get_data()
    if data is not None and data.valid:
        print(data.position, data.quaternion, data.gripper, data.buttons)
```

- `PikaTeleopDevice(pika_sense_port=None, vive_tracker_id=None, use_gripper=True, gripper_deadband=2.0)` —— 包装 `PikaDevice`，另提供 `get_command_state()`。
- `UmiTeleopDevice(serial_number, use_gripper=True, use_vive_tracker=False, vive_tracker_id='WM0')` —— 包装 `XVLib`（配置时叠加 `ViveTracker`）。
- `GelloTeleopDevice(port=None, joint_ids=(1,...,7), joint_signs=(1,...,1), start_joints=..., gripper_id=8, torque_joint_ids=None)` —— 使用 `GelloDevice` 完成标定与 `GelloAgent` 创建。
- `XboxTeleopDevice(axes_deadzone=..., max_distances=..., direction=0)` —— 包装 `XBoxDevice`，`get_data()` 返回 `CARTESIAN_DELTA` 帧；`dz` / `drz` 的符号（方向键/反转开关）由调用方处理。
- `SpacemouseTeleopDevice(axes_deadzone=..., max_distances=..., direction=0)` —— 包装 `SpaceDevice`，返回 `CARTESIAN_DELTA` 帧，`buttons` 为 `LEFT` / `RIGHT`。

所有设备实现 `TeleopDevice`（`connect`、`close`、`get_data`），支持 `with` 用法。底层 SDK 对象仍可通过 `pika_sense`、`xvlib`、`tracker`、`gello_agent` 访问，便于采集原始数据与相机图像。Xbox / SpaceMouse 入口有意保留启停长按、调平、回零、模式切换等状态机：它们属于控制器行为而非设备读数。

`CartesianTeleopMapper(tracker_to_robot_eef, robot_base_pose=None, is_axis_angle=True)` 将笛卡尔 `TeleopData` 映射为机器人目标位姿 `[x, y, z, rx, ry, rz]`（mm/rad），采用相对运动：目标 = 机械臂初始位姿 × inv(遥操作初始位姿) × 当前遥操作位姿。遥操作开始时调用 `reset(data, robot_tcp_pose)`（配置了 `robot_base_pose` 时省略该位姿），之后每帧调用 `map(data)`。内部复用 `Transformations.tracker_pose_to_robot_matrix()` / `tracker_robot_matrix_to_robot_pose()`。

不连接机器人、仅录制数据见 [`data_collection/collect_data.py`](../../data_collection/collect_data.py)。

## devices/pika/ —— Pika Sense 与 Pika Gripper

`from uf_teleop_core.devices.pika import PikaDevice`

- `get_serial_ports(vidpid='1a86:7522')` —— 按 VID:PID 枚举候选串口。
- `check_pika_device(port)` —— 探测串口上的设备类型。返回 `-1` 串口打不开、`0` 非 Pika 设备、`1` Pika Sense、`2` Pika Gripper。
- `PikaDevice(dev_type=1, pika_sense_port=None, pika_gripper_port=None)` —— `dev_type` 取 `1` 只用 Sense、`2` 只用 Gripper、`3` 两者都用。不传端口时自动扫描并探测。
- `pika_sense` / `pika_gripper` 属性在首次访问时才真正连接设备。同一串口的句柄在类级 `PIKA_DEVICE_MAP` 中复用，所以 `UFRobot` 的 Pika 夹爪和遥操作脚本可以共享同一个 Sense 实例。

需要 `agx-pypika`（提供 `pika.sense` / `pika.gripper` 模块），在属性内部延迟导入。

## devices/umi/ —— FastUMI 与 Vive Tracker

`from uf_teleop_core.devices.umi import XVLib, Transformations` / `from uf_teleop_core.devices.umi import ViveTracker`

### xvlib/

`XVLib(serial_number, init_slam=False, init_clamp_stream=False, init_color_camera=False, init_fisheye_cameras=False)`

对 `libxvlib.so` 的 ctypes 封装，负责枚举设备并按需初始化各路数据流。遥操作常用的几组调用：

- `xv_get_devices()` —— 枚举在线的 FastUMI 设备。
- `xv_get_slam_pose()` / `xv_get_slam_data()` —— 取内置 SLAM 的位姿。
- `xv_get_clamp_stream_data()` —— 取夹爪开合数据。
- `xv_get_color_camera_data()` / `xv_get_fisheye_cameras_data()` —— 取相机图像（返回 numpy 帧，需要 `opencv-python`）。

装载顺序为：检查系统 XVSDK → 预加载 `libtbb.so.2` → 加载 `libopencv_*.so` → 加载 `libxvlib.so`。仓库内附带了这几个 `.so` 作为兜底，随包分发；随附的 `libopencv_core.so.4.2` 依赖旧版 TBB ABI，而 Ubuntu 22.04+ 的 oneAPI TBB（`libtbb.so.12`）与之不兼容，因此代码会显式预加载 `libtbb.so.2`。系统未安装 XVSDK 时抛出异常并给出安装命令。注意：包含这些 `.so` 的 wheel 必须按 Linux x86_64 平台构建。

### vive_tracker/

- `ViveTracker(config_path=None, lh_config=None, args=None)` —— 单例（`SingletonMeta`），后台线程持续采集位姿。`get_pose(device_name=None)` 取位姿、`get_raw_pose()` 取原始位姿、`get_tracked_device_names()` 列出被跟踪设备、`stop()` / `close()` 释放。
- `Transformations` —— 纯静态工具类：四元数、旋转矩阵、RPY、轴角互转，以及 `tracker_pose_to_robot_matrix()` / `tracker_robot_matrix_to_robot_pose()` 做 Tracker 位姿到机器人位姿的映射。现位于 `uf_teleop_core.transformations`，此处保留 re-export 以兼容旧用法。

## devices/xbox/ —— Xbox 兼容手柄

`from uf_teleop_core.devices.xbox import XBoxDevice`

- `XBoxDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.2, 0.2, 0.1], logger=None)` —— `threading.Thread` 子类，daemon 线程持续读取手柄输入。
- Linux 且安装了 `evdev` 时优先使用 `evdev`，否则回退到 `inputs` 包。
- `connected` 指示连接状态；`state` 提供摇杆、扳机、按键与方向键；`set_axes_deadzone()` 可运行时调整死区。

## devices/spacemouse/ —— 3Dconnexion SpaceMouse

`from uf_teleop_core.devices.spacemouse import SpaceDevice`

- `SpaceDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.15, 0.15, 0.1], logger=None)` —— 同样是后台线程。
- HID 后端：非 Windows 平台固定使用 HIDAPI；Windows 下可用环境变量 `SPACEMOUSE_BACKEND` 指定 `hidapi`、`hid` 或 `pywinusb`，未指定时优先 `pywinusb`、回退 HIDAPI。
- `list_space_devices()` 列出可用设备；`connected`、`product_name`、`vendor_name`、`vendor_id`、`product_id` 提供设备信息；`state` 提供六轴与按键；`set_led(state)` 控制指示灯；`register_state_changed_callback(cb)` 注册状态回调。

## devices/gello/ —— Gello 主手

`from uf_teleop_core.devices.gello import GelloDevice`

- `GelloDevice(port=None, joint_ids=..., joint_signs=..., start_joints=..., gripper_id=8, torque_joint_ids=None)` —— 在 `connect()` 内延迟导入 `gello` 包。
- `connect()` 读取当前主手关节角、计算零位偏移、按需开启力矩模式，并创建 `GelloAgent`。
- `get_action()` 返回 `[joints..., gripper]`（`gripper_id < 0` 时仅关节），并暴露 `action_dim`、`gripper_id`；`close()` 释放 agent 引用。

## 依赖

| 模块 | 依赖 | 说明 |
| --- | --- | --- |
| `robot/` | `xarm-python-sdk` | 所有方案共用。 |
| `devices/pika/` | `agx-pypika`、`pyserial` | `agx-pypika` 提供 `pika` 模块；请用 `--no-deps` 安装以跳过其 GUI/相机依赖。 |
| `devices/umi/xvlib/` | 系统 XVSDK（`libxvsdk.so`）、`opencv-python` | 缺 XVSDK 时会给出 deb 安装命令；图像帧需要 OpenCV。 |
| `devices/umi/vive_tracker/` | `pysurvive` | 仅在使用 HTC Vive Tracker 时需要；请用 `--no-deps` 安装以跳过 `gooey`。 |
| `devices/xbox/` | `inputs`，Linux 可选 `evdev` | `evdev` 存在时优先。 |
| `devices/spacemouse/` | `hidapi`（导入名 `hid`），Windows 可选 `pywinusb` | 见上文后端选择规则。 |
| `devices/gello/` | `gello`（固定 commit 的 GitHub archive）、`dynamixel-sdk`（PyPI） | 由 `gello` extra 安装。使用 archive 可避免 pip 拉取 gello 未使用的 git 子模块。 |

以上依赖均在根 `pyproject.toml` 中以 extras 声明；各方案目录下的 `requirements.txt` 与对应 extra 保持一致。

## 安全提示

- `UFRobot(config)` 在构造时就连接控制器并运动到 `start_joints`，实例化即会驱动机械臂。
- `send_action()` 返回控制器错误码，调用方应在循环中检查并在非 0 时退出（各方案脚本已如此处理）。
- 首次运行建议调低 `robot_speed` 与 `robot_acc`，并安排人员看守急停。
