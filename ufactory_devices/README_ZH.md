# ufactory_devices

五套遥操作方案共享的核心库。各方案自己的脚本只负责「读取输入 → 计算映射 → 下发动作」的循环，所有与硬件打交道的代码集中在这里：xArm 机械臂封装和四类输入设备驱动。

## 目录结构

```
ufactory_devices/
├── robot/
│   └── uf_robot.py            # UFRobot：xArm 连接、运动、夹爪控制
├── pika/
│   └── pika_device.py         # PikaDevice：Pika Sense / Pika Gripper 串口驱动
├── umi/
│   ├── xvlib/
│   │   ├── xvlib.py           # XVLib：libxvlib.so 的 ctypes 封装
│   │   ├── libxvlib.so        # 随仓库附带的库（Linux x86_64）
│   │   ├── libopencv_core.so.4.2
│   │   ├── libopencv_imgproc.so.4.2
│   │   └── libtbb.so.2
│   └── vive_tracker/
│       ├── vive_tracker.py    # ViveTracker：基于 pysurvive 的 Tracker 驱动
│       └── transformations.py # Transformations：位姿数学工具
├── xbox/
│   └── xbox_device.py         # XBoxDevice：Xbox 兼容手柄驱动
└── spacemouse/
    └── space_device.py        # SpaceDevice：3Dconnexion SpaceMouse 驱动
```

顶层 `__init__.py` 为空，请按子包显式导入，例如 `from ufactory_devices.robot import UFRobot`。

## 各方案使用的模块

| 遥操作方案 | 从 ufactory_devices 引入 |
| --- | --- |
| [pika_teleop](../pika_teleop/README_ZH.md) | `robot.UFRobot`、`pika.PikaDevice`、`umi.Transformations` |
| [umi_teleop](../umi_teleop/README_ZH.md) | `robot.UFRobot`、`umi.XVLib`、`umi.Transformations` |
| [gello_teleop](../gello_teleop/README_ZH.md) | `robot.UFRobot` |
| [xbox_teleop](../xbox_teleop/README_ZH.md) | `robot.UFRobot`、`xbox.XBoxDevice` |
| [spacemouse_teleop](../spacemouse_teleop/README_ZH.md) | `robot.UFRobot`、`spacemouse.SpaceDevice` |

## robot/ —— xArm 机械臂封装

`from ufactory_devices.robot import UFRobotConfig, UFRobot`

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

- `UFRobot(config)` —— 构造时即连接控制器、使能电机、清除错误，并运动到 `start_joints`。**实例化就会驱动机械臂**，务必先确认工作空间。
- `send_action(action)` —— 各方案统一的下发接口，按 `robot_mode` 分派：
  - `robot_mode: 6`：`action[:轴数]` 为关节角（rad），`action[轴数]` 为夹爪归一化值（0 张开 → 1 闭合）。
  - `robot_mode: 7` 与其他：`action[:6]` 为 `[x, y, z, rx, ry, rz]`，`action[6]` 为夹爪归一化值。
  - 夹爪按类型分别走 TDK Modbus（xArm Gripper G1/G2、BIO Gripper G2、Robotiq）或串口（Pika Gripper）。
  - 返回控制器错误码，调用方应在循环中检查，非 0 时退出。
- `get_position(is_axis_angle=False)` —— 读取当前位姿（默认 xyzrpy，可选轴角）。
- `robot_init(enable=True, init_gripper_pose=False)` —— 重置模式与状态，并按需初始化夹爪。

`uf_robot.py` 顶层导入 `PikaDevice`，因此 `import ufactory_devices.robot` 会连带导入 `pika` 子包；但 `agx-pypika` 本身是延迟导入的，不使用 Pika 夹爪时无需安装。

## pika/ —— Pika Sense 与 Pika Gripper

`from ufactory_devices.pika import PikaDevice`

- `get_serial_ports(vidpid='1a86:7522')` —— 按 VID:PID 枚举候选串口。
- `check_pika_device(port)` —— 探测串口上的设备类型。返回 `-1` 串口打不开、`0` 非 Pika 设备、`1` Pika Sense、`2` Pika Gripper。
- `PikaDevice(dev_type=1, pika_sense_port=None, pika_gripper_port=None)` —— `dev_type` 取 `1` 只用 Sense、`2` 只用 Gripper、`3` 两者都用。不传端口时自动扫描并探测。
- `pika_sense` / `pika_gripper` 属性在首次访问时才真正连接设备。同一串口的句柄在类级 `PIKA_DEVICE_MAP` 中复用，所以 `UFRobot` 的 Pika 夹爪和遥操作脚本可以共享同一个 Sense 实例。

需要 `agx-pypika`（提供 `pika.sense` / `pika.gripper` 模块），在属性内部延迟导入。

## umi/ —— FastUMI 与 Vive Tracker

`from ufactory_devices.umi import XVLib, Transformations` / `from ufactory_devices.umi import ViveTracker`

### xvlib/

`XVLib(serial_number, init_slam=False, init_clamp_stream=False, init_color_camera=False, init_fisheye_cameras=False)`

对 `libxvlib.so` 的 ctypes 封装，负责枚举设备并按需初始化各路数据流。遥操作常用的几组调用：

- `xv_get_devices()` —— 枚举在线的 FastUMI 设备。
- `xv_get_slam_pose()` / `xv_get_slam_data()` —— 取内置 SLAM 的位姿。
- `xv_get_clamp_stream_data()` —— 取夹爪开合数据。
- `xv_get_color_camera_data()` / `xv_get_fisheye_cameras_data()` —— 取相机图像（返回 numpy 帧，需要 `opencv-python`）。

装载顺序为：检查系统 XVSDK → 预加载 `libtbb.so.2` → 加载 `libopencv_*.so` → 加载 `libxvlib.so`。仓库内附带了这几个 `.so` 作为兜底；随附的 `libopencv_core.so.4.2` 依赖旧版 TBB ABI，而 Ubuntu 22.04+ 的 oneAPI TBB（`libtbb.so.12`）与之不兼容，因此代码会显式预加载 `libtbb.so.2`。系统未安装 XVSDK 时抛出异常并给出安装命令。

### vive_tracker/

- `ViveTracker(config_path=None, lh_config=None, args=None)` —— 单例（`SingletonMeta`），后台线程持续采集位姿。`get_pose(device_name=None)` 取位姿、`get_raw_pose()` 取原始位姿、`get_tracked_device_names()` 列出被跟踪设备、`stop()` / `close()` 释放。
- `Transformations` —— 纯静态工具类：四元数、旋转矩阵、RPY、轴角互转，以及 `tracker_pose_to_robot_matrix()` / `tracker_robot_matrix_to_robot_pose()` 做 Tracker 位姿到机器人位姿的映射。

注意 `transformations.py` 位于 `umi/vive_tracker/` 下而非顶层，`umi.Transformations` 是从这里再导出的；pika_teleop 也使用它做位姿换算。

## xbox/ —— Xbox 兼容手柄

`from ufactory_devices.xbox import XBoxDevice`

- `XBoxDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.2, 0.2, 0.1], logger=None)` —— `threading.Thread` 子类，daemon 线程持续读取手柄输入。
- Linux 且安装了 `evdev` 时优先使用 `evdev`，否则回退到 `inputs` 包。
- `connected` 指示连接状态；`state` 提供摇杆、扳机、按键与方向键；`set_axes_deadzone()` 可运行时调整死区。

## spacemouse/ —— 3Dconnexion SpaceMouse

`from ufactory_devices.spacemouse import SpaceDevice`

- `SpaceDevice(axes_deadzone=[0.15, 0.15, 0.1, 0.15, 0.15, 0.1], logger=None)` —— 同样是后台线程。
- HID 后端：非 Windows 平台固定使用 HIDAPI；Windows 下可用环境变量 `SPACEMOUSE_BACKEND` 指定 `hidapi`、`hid` 或 `pywinusb`，未指定时优先 `pywinusb`、回退 HIDAPI。
- `list_space_devices()` 列出可用设备；`connected`、`product_name`、`vendor_name`、`vendor_id`、`product_id` 提供设备信息；`state` 提供六轴与按键；`set_led(state)` 控制指示灯；`register_state_changed_callback(cb)` 注册状态回调。

## 依赖

| 模块 | 依赖 | 说明 |
| --- | --- | --- |
| `robot/` | `xarm-python-sdk` | 所有方案共用。 |
| `pika/` | `agx-pypika`、`pyserial` | `agx-pypika` 提供 `pika` 模块，仅在实际使用 Pika Sense/Gripper 时需要。 |
| `umi/xvlib/` | 系统 XVSDK（`libxvsdk.so`）、`opencv-python` | 缺 XVSDK 时会给出 deb 安装命令；图像帧需要 OpenCV。 |
| `umi/vive_tracker/` | `pysurvive` | 仅在使用 HTC Vive Tracker 时需要。 |
| `xbox/` | `inputs`，Linux 可选 `evdev` | `evdev` 存在时优先。 |
| `spacemouse/` | `hidapi`（导入名 `hid`），Windows 可选 `pywinusb` | 见上文后端选择规则。 |

各方案目录下的 `requirements.txt` 只列出该方案实际用到的部分，安装方式见根目录 [README_ZH.md](../README_ZH.md)。

## 安全提示

- `UFRobot(config)` 在构造时就连接控制器并运动到 `start_joints`，实例化即会驱动机械臂。
- `send_action()` 返回控制器错误码，调用方应在循环中检查并在非 0 时退出（各方案脚本已如此处理）。
- 首次运行建议调低 `robot_speed` 与 `robot_acc`，并安排人员看守急停。
