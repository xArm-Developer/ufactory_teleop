# Gello Teleoperation System

Use a Gello leader arm to teleoperate a UFACTORY xArm robot in joint space.

GitHub: https://github.com/xArm-Developer/ufactory_teleop

This document is based on `gello_teleop/uf_robot_gello_teleop.py`. It explains how to use a Gello/Dynamixel leader arm with a UFACTORY xArm robot.

## 1. Introduction

The entry script reads Gello joint positions through the Dynamixel serial bus, converts them into robot joint targets with `GelloAgent`, and sends all robot commands through the unified `UFRobot.send_action()` interface.

Main components:

- `gello_teleop/uf_robot_gello_teleop.py`: Gello teleoperation entry script.
- `gello_teleop/config/*.yaml`: example configurations for xArm5, xArm6, and xArm7.
- `ufactory_devices/robot/uf_robot.py`: xArm connection, initialization, joint motion, and gripper control wrapper.

Supported features:

- Joint-space teleoperation for xArm5, xArm6, and xArm7.
- Automatic Gello joint offset calculation at startup.
- Configurable Gello joint mapping through `joint_ids` and `joint_signs`.
- Optional Gello gripper joint, sent as the last action value.
- Optional torque mode for unused or locked Dynamixel joints through `torque_joint_ids`.
- Unified robot command path through `send_action`; this entry requires `robot_mode: 6`.

## 2. Environment and Hardware Requirements

Recommended environment:

- Ubuntu 20.04, Ubuntu 22.04, or Ubuntu 24.04.
- Python 3.8, 3.9, or 3.10.
- UFACTORY xArm robot.
- Gello leader arm.
- Dynamixel USB serial adapter.
- Optional Gello-side Dynamixel gripper joint.
- Optional robot-side gripper, such as xArm Gripper, xArm Gripper G2, or another gripper supported by `UFRobot`.

Before running, make sure:

- The control computer can reach the xArm controller IP.
- The current user can access the Gello Dynamixel serial device.
- The xArm is ready to be enabled and the emergency stop is released.

## 3. Installation

Clone the project and enter the Gello teleoperation directory:

```bash
git clone https://github.com/xArm-Developer/ufactory_teleop
cd ufactory_teleop/gello_teleop
```

Create and activate a virtual environment:

```bash
conda create --name py39 python=3.9
conda activate py39
```

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install pysurvive agx-pypika --no-deps
git clone https://github.com/wuphilipp/gello_software.git /tmp/gello_software
cd /tmp/gello_software
pip install .
cd -
rm -rf /tmp/gello_software
```

After installation, verify the following imports work:

```bash
python -c "from gello.dynamixel.driver import DynamixelDriver; from gello.agents.gello_agent import GelloAgent;from xarm.wrapper import XArmAPI"
```

Configure serial permissions:

```bash
sudo usermod -aG dialout $USER
```

After running this command, log in again or reconnect the Gello Dynamixel USB serial adapter.

## 4. Configuration File

Example configuration files:

```bash
gello_teleop/config/xarm7_gello_teleop.yaml
gello_teleop/config/xarm6_gello_teleop.yaml
gello_teleop/config/xarm5_gello_teleop.yaml
```

xArm7 example:

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

| Parameter | Description |
| --- | --- |
| `robot_ip` | IP address of the xArm controller. |
| `robot_mode` | Robot motion mode. This Gello entry must use `6`, which means joint control mode. |
| `robot_speed` | Joint speed in deg/s. `UFRobot` converts it to rad/s in mode 6. |
| `robot_acc` | Joint acceleration in deg/s^2. `UFRobot` converts it to rad/s^2 in mode 6. |
| `gripper_type` | Robot-side gripper type. `0` no gripper, `1` xArm Gripper, `2` xArm Gripper G2, `3` BIO Gripper G2, `10` Pika Gripper, `11` Robotiq Gripper. |
| `gripper_port` | Pika Gripper serial port, only used when `gripper_type: 10`. |
| `gripper_speed` | Gripper speed. `-1` uses the default value. |
| `gripper_force` | Gripper force parameter. `-1` uses the default value. |
| `start_joints` | Robot joint position to move to during startup, in rad. The length must match the robot axis count. |
| `start_tcp_pose` | Optional TCP pose after reaching `start_joints`, in `[x, y, z, roll, pitch, yaw]`; position is in mm and orientation is in rad. |

### TeleoperatorConfig

| Parameter | Description |
| --- | --- |
| `fps` | Control loop frequency. Default is `30`. |
| `port` | Gello Dynamixel serial port path, such as `/dev/serial/by-id/...`. |
| `joint_ids` | Gello Dynamixel IDs used for robot joint mapping. For xArm7, the default is `[1, 2, 3, 4, 5, 6, 7]` if omitted. |
| `joint_signs` | Direction sign for each Gello joint. Length must match `joint_ids`. For xArm7, the default is all `1` if omitted. |
| `start_joints` | Robot joint angles corresponding to the Gello startup reference pose, in rad. Length must match `joint_ids`. |
| `gripper_id` | Gello gripper Dynamixel ID. Set to `-1` to disable the Gello gripper. |
| `torque_joint_ids` | Dynamixel IDs that should be put into torque mode. This is commonly used for physical Gello joints that are not mapped on xArm5/xArm6 setups. |

## 5. Gello Pose Alignment

At startup, the script reads the current Gello joint angles and automatically computes joint offsets:

```python
offset = curr_joints[i] - start_joints[i] / joint_signs[i]
```

Therefore, before running the script, place the Gello leader arm at the reference pose represented by `TeleoperatorConfig.start_joints`.

Notes:

- `RobotConfig.start_joints` is the robot startup pose.
- `TeleoperatorConfig.start_joints` is the robot joint reference corresponding to the current Gello startup pose.
- These two values are usually kept the same unless you intentionally need a different mapping reference.
- If Gello is not placed at the reference pose before startup, the robot target joints will be shifted.
- In xArm5/xArm6 examples, some physical Gello joints are not mapped and are fixed through `torque_joint_ids`.

## 6. Running

Enter the Gello teleoperation directory:

```bash
cd ufactory_teleop/gello_teleop
# xArm7
python uf_robot_gello_teleop.py --config config/xarm7_gello_teleop.yaml

# xArm6
python uf_robot_gello_teleop.py --config config/xarm6_gello_teleop.yaml

# xArm5
python uf_robot_gello_teleop.py --config config/xarm5_gello_teleop.yaml
```

## 7. Safety Notes

- Make sure the robot workspace is clear before starting the script.
- The robot connects and moves to `RobotConfig.start_joints` before the Enter prompt appears.
- Use lower `robot_speed` and `robot_acc` for first tests.
- Place Gello at the pose represented by `TeleoperatorConfig.start_joints` before starting the script.
- Before pressing Enter, confirm again that both the robot and Gello are in safe poses.
- Keep the emergency stop supervised during debugging.
- Set `gripper_id: -1` if the Gello side has no gripper.
- Set `gripper_type: 0` if the robot side has no gripper.
- If the robot returns a non-zero error code, the control loop exits.

## 8. Troubleshooting

### `Gello teleop requires robot_mode=6 joint control mode`

This entry script only supports joint control mode. Set:

```yaml
RobotConfig:
  robot_mode: 6
```

### `joint_signs and joint_ids length mismatch`

`TeleoperatorConfig.joint_signs` and `TeleoperatorConfig.joint_ids` have different lengths. Check the number of elements in both lists.

### `start_joints and joint_ids length mismatch`

`TeleoperatorConfig.start_joints` and `TeleoperatorConfig.joint_ids` have different lengths. Make sure every mapped Gello joint has one reference joint angle.

### `Joint action length must be ...`

`GelloAgent` returned an action with a length different from the expected `_action_dim`. Check `joint_ids`, `gripper_id`, and the Gello hardware configuration.

### Cannot open the Gello serial port

Check:

- Whether `TeleoperatorConfig.port` is correct.
- Whether the USB serial adapter is connected.
- Whether the current user has serial permissions.
- Whether another process is using the same serial port.

### The robot does not move after pressing Enter

Check:

- Whether the xArm controller IP is correct.
- Whether the robot is in an error or emergency stop state.
- Whether the UFACTORY SDK can control the robot independently.
- Whether Gello is returning a valid action.

