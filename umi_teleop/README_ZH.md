# UMI 遥操作系统



## 系统要求

### 操作系统
- **支持**: Ubuntu 22.04/Ubuntu 24.04
- **不支持**: Windows/Mac OS

### Python 版本
- Python 3.8/3.9/3.10

### 硬件要求
- UFACTORY xArm 机械臂(xArm 5/6/7, Lite 6或850)
- FAST UMI PRO

## 安装

### 1. 下载项目

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/umi_teleop
```

### 2. 创建虚拟环境与安装依赖

创建虚拟环境(推荐)
```bash
python3.9 -m venv py39
```
激活虚拟环境
```bash
source py39/bin/activate
```

安装XVSDK
```bash
dpkg -i xvsdk/XVSDK_focal_amd64.deb
apt install -y --fix-broken
```

安装依赖
```bash
pip install -r requirements.txt
pip install pysurvive
```

设置USB权限 (需要设置USB的读写权限，下面指令可以自动设置，运行完指令后请插拔一次USB)
```bash
sudo cp rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

系统启动参数配置（注: 多个umi设备同时使用才需要）
```bash
sed -i '/GRUB_CMDLINE_LINUX_DEFAULT/s/quiet splash/quiet splash usbcore.usbfs_memory_mb=128/' /etc/default/grub
sync
update-grub
reboot
```

跟踪设备校准 (首次使用UMI设备 或者**基站位置变动**需要校准)
```bash
# 校准过程不要移动基站和tracker设备
# 校准会先删除原有的配置文件
# 然后校准
# 校准完会持续输出tracker的位置(请确定有对应的tracker位置输出)
python calibrate.py
```

## 使用说明

### 基本用法

```bash
# 单个umi设备控制单个机械臂（***运行前请先修改配置文件***）
python uf_robot_umi_teleop.py --config config/xarm6_umi_teleop.yaml

# 两个umi设备控制两个机械臂（***运行前请先修改配置文件***）
python uf_robot_umi_teleop_dual.py --config config/xarm6_umi_teleop_dual.yaml
```

### 参数说明()

#### RobotConfig
- `robot_ip`: 机械臂的 IP 地址，例如 192.168.1.200
- `robot_mode`: 
    - `1`: Servo 伺服运动模式
    - `7`: 笛卡尔在线轨迹规划模式 (推荐)
- `robot_speed`: 机械臂运动速度 (默认250)
- `robot_acc`: 机械臂运动加速度 (默认1000)
- `gripper_type`:
    - `0`: 无夹爪
    - `1`: xArm Gripper
    - `2`: xArm Gripper G2
    - `3`: BIO Gripper G2
    - `10`: Pika Gripper
    - `11`: RobotIQ Gripper
- `start_joints`: 启动时机械臂会使用关节指令运动到此位置
- `start_tcp_pose`: 启动时机械臂在运动到start_joints后会使用笛卡尔指令运动到此位置 (不指定则不执行)

#### TeleoperatorConfig
- `serial_number`: UMI设备的序列号
- `use_gripper`: 是否控制机械爪
- `use_vive_tracker`: 是否使用vive tracker, 否则使用光流
- `vive_tracker_id`: vive tracker的ID (默认'WM0'), 如果有多个设备, 请使用设备ID (LHR-******)
- `tracker_to_robot_eef`: 从tracker到机械臂末端法兰中心的转换关系
- `robot_base_pose`: 对应的机械臂位置([x(mm), y(mm), z(mm), roll(rad), pitch(rad), yaw(rad)])
