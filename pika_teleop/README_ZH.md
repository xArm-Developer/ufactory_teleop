# Pika 遥操作系统

使用松灵机器人的Pika Sense (https://global.agilex.ai/products/pika) 进对 UFACTORY(深圳市众为创造科技有限公司) 的机械臂(https://www.ufactory.cc/xarm-collaborative-robot/)的遥操作控制。  

GitHub: https://github.com/xArm-Developer/ufactory_teleop

[![Watch the video](../assets/pika_teleoperation_system.jpg)](https://www.bilibili.com/video/BV1791rB4Egk/?spm_id_from=333.1387.homepage.video_card.click&vd_source=9cdbfdb03a35ac858f97ba3ca89dc358)



## 系统要求

### 操作系统
- **支持**: Ubuntu 22.04/Ubuntu 24.04
- **不支持**: Windows/Mac OS

### Python 版本
- Python 3.8/3.9/3.10

### 硬件要求
- UFACTORY xArm 机械臂(xArm 5/6/7, Lite 6或850)
- Pika Sense

## 安装

### 1. 下载项目

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/pika_teleop
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

安装依赖
```bash
pip install -r requirements.txt
pip install pysurvive
pip install pika
```

## 使用说明

### 基本用法

```bash
python uf_robot_pika_teleop.py <robot_ip> [robot_mode] [gripper_type]
```

### 参数说明

#### 必需参数
- `robot_ip`: 机械臂的 IP 地址，例如 192.168.1.200

#### 可选参数

**robot_mode** (默认: 7)
- `1`: Servo 伺服运动模式
- `7`: 笛卡尔在线轨迹规划模式 (推荐)

**gripper_type** (默认: 0)
- `0`: 无夹爪
- `1`: xArm Gripper
- `2`: xArm Gripper G2
- `3`: BIO Gripper G2

### 使用方法

#### 1. 设置USB权限

需要设置USB的读写权限，下面指令可以自动设置，运行完指令后请插拔一次USB。
```bash
sudo cp 81-vive.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

#### 2. 跟踪设备校准

首次使用Pika Sense 或者**基站位置变动**需要校准。

* 方法一：使用srvive-cliu.py 进行校准 [推荐]   


1. 先运行官方示例：
```bash
git clone https://github.com/collabora/libsurvive.git
cd libsurvive/bindings/python/examples
python example.py 
```

返回示例:
```bash
Info: Loaded drivers: GlobalSceneSolver, HTCVive
Info: Adding tracked object WM0 from HTC
Info: Device WM0 has watchman FW version 1592875850 and FPGA version 538/7/2; named '                       watchman'. Hardware id 0x84020109 Board rev: 3 (len 56)
Info: Detected LH gen 2 system.
Info: LightcapMode (WM0) 1 -> 2 (ff)
Info: Adding lighthouse ch 1 (idx: 0, cnt: 1)
Info: OOTX not set for LH in channel 1; attaching ootx decoder using device WM0
Info: Adding lighthouse ch 0 (idx: 1, cnt: 2)
Info: OOTX not set for LH in channel 0; attaching ootx decoder using device WM0
Info: (0) Preamble found
Info: (1) Preamble found
Info: Got OOTX packet 0 bdeb5b80
Info: Got OOTX packet 1 36df43d7
Info: MPFIT success 1093702.051384/52.2148055877/0.0001598 (21 measurements, 1, MP_OK_CHI, 5 iters, up err 0.0002584, trace 0.0000177)
Info: Global solve with 1 scenes for 1 with error of 1093702.051384/52.2148055877 (acc err 0.0003)
Info: Using LH 1 (bdeb5b80) as reference lighthouse
LH1: T: 1761879738.310068 P:  0.000000, 0.583524, 0.721219 R: -0.445283,-0.223126,-0.379739,-0.779574
WM0: T: 1761879738.470426 P: -0.012316,-0.005824,-0.008128 R:  0.165526, 0.956895, 0.235385, 0.039320
WM0: T: 1761879738.474582 P: -0.012323,-0.005919,-0.008163 R:  0.166495, 0.956762, 0.235292, 0.039036
```

2. 运行srvive-cliu.py

```bash
python survive-cli.py
```
返回示例:

```
Info: Loaded drivers: GlobalSceneSolver, HTCVive
Info: Adding tracked object WM0 from HTC
Info: Device WM0 has watchman FW version 1592875850 and FPGA version 538/7/2; named '                       watchman'. Hardware id 0x84020109 Board rev: 3 (len 56)
Info: Detected LH gen 2 system.
Info: LightcapMode (WM0) 1 -> 2 (ff)
Info: OOTX not set for LH in channel 1; attaching ootx decoder using device WM0
Info: OOTX not set for LH in channel 0; attaching ootx decoder using device WM0
Info: MPFIT success 7032214.017596/263.9077546656/0.0001747 (53 measurements, 1, MP_OK_CHI, 167 iters, up err 0.0026960, trace 0.0001336)
Info: Global solve with 1 scenes for 0 with error of 7032214.017596/263.9077546656 (acc err 0.0025)
Info: Global solve with 1 scenes for 1 with error of 7032214.017596/263.9077546656 (acc err 0.0034)
Info: Using LH 0 (36df43d7) as reference lighthouse
```


* 方法二：使用松灵机器人提供的ROS包的指令校准(适用于ROS1/2开发者)

参考文档 https://agilexsupport.yuque.com/staff-hso6mo/peoot3/axi8hh9h9t2sh2su

#### 3. 运行遥操作示例 : 使用笛卡尔在线规划模式，使用机械爪G2
```bash
python uf_robot_pika_teleop.py 192.168.1.100 7 2
```

* 开始遥操作: 快速张开/闭合Pika Sense的夹子2次，注意启动时Pika Sense的姿态和方向将作为机械臂初始姿态和方向。
* 结束遥操作: 快速张开/闭合Pika Sense的夹子2次

