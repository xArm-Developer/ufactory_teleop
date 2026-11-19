#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""独立使用 Teleop 设备（可选叠加 Robot 状态）进行数据采集。

示例:
    python data_collection/collect_data.py --teleop-type pika \
        -c pika_teleop/config/xarm6_pika_teleop.yaml -o data/pika_ep001.jsonl

每帧写入一行 JSON。默认只连接遥操作设备；--with-robot 时额外连接机械臂并
记录其状态（注意: UFRobot 初始化会移动机械臂到 start_joints，采集中不发送动作）。

运行前需在仓库根目录安装核心库，例如 `pip install -e ".[pika]"`（按设备选择 extra）。
"""

import sys
import json
import time
import yaml
import logging
import argparse
from pathlib import Path

import numpy as np

from uf_teleop_core.teleop.pika_teleop_device import PikaTeleopDevice
from uf_teleop_core.teleop.umi_teleop_device import UmiTeleopDevice
from uf_teleop_core.teleop.gello_teleop_device import GelloTeleopDevice
from uf_teleop_core.teleop.xbox_teleop_device import XboxTeleopDevice
from uf_teleop_core.teleop.spacemouse_teleop_device import SpacemouseTeleopDevice

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('collect_data')

DEFAULT_GELLO_JOINTS = (1, 2, 3, 4, 5, 6, 7)


def build_teleop(kind, cfg):
    """根据类型构建遥操作设备。"""
    if kind == 'pika':
        return PikaTeleopDevice(
            pika_sense_port=cfg.get('pika_sense_port'),
            vive_tracker_id=cfg.get('vive_tracker_id'),
            use_gripper=cfg.get('use_gripper', True),
        )
    if kind == 'umi':
        if 'serial_number' not in cfg:
            raise ValueError('UMI TeleoperatorConfig 缺少 serial_number')
        return UmiTeleopDevice(
            serial_number=cfg['serial_number'],
            use_gripper=cfg.get('use_gripper', True),
            use_vive_tracker=cfg.get('use_vive_tracker', False),
            vive_tracker_id=cfg.get('vive_tracker_id', 'WM0'),
        )
    if kind == 'gello':
        torque_joint_ids = cfg.get('torque_joint_ids')
        return GelloTeleopDevice(
            port=cfg.get('port'),
            joint_ids=tuple(cfg.get('joint_ids', DEFAULT_GELLO_JOINTS)),
            joint_signs=tuple(cfg.get('joint_signs', (1,) * len(cfg.get('joint_ids', DEFAULT_GELLO_JOINTS)))),
            start_joints=tuple(cfg.get('start_joints', (0, 0, 0, np.pi / 2, 0, np.pi / 2, 0))),
            gripper_id=cfg.get('gripper_id', 8),
            torque_joint_ids=tuple(torque_joint_ids) if torque_joint_ids else None,
        )
    if kind == 'xbox':
        return XboxTeleopDevice(
            axes_deadzone=tuple(cfg.get('axes_deadzone', (0.15, 0.15, 0.1, 0.2, 0.2, 0.1))),
            max_distances=tuple(cfg.get('max_distances', (500, 500, 500, 60, 60, 60))),
            direction=cfg.get('direction', 0),
        )
    if kind == 'spacemouse':
        return SpacemouseTeleopDevice(
            axes_deadzone=tuple(cfg.get('axes_deadzone', (0.15, 0.15, 0.10, 0.15, 0.15, 0.10))),
            max_distances=tuple(cfg.get('max_distances', (500, 500, 500, 60, 60, 60))),
            direction=cfg.get('direction', 0),
        )
    raise ValueError('不支持的 teleop 类型: {}'.format(kind))


def _to_list(value):
    if value is None:
        return None
    return np.asarray(value, dtype=float).reshape(-1).tolist()


def frame_to_dict(data, robot_state=None):
    frame = {
        'timestamp': round(data.timestamp, 6),
        'space': data.space.value,
        'valid': data.valid,
    }
    if data.position is not None:
        frame['position'] = _to_list(data.position)
    if data.quaternion is not None:
        frame['quaternion'] = _to_list(data.quaternion)
    if data.joints is not None:
        frame['joints'] = _to_list(data.joints)
    if data.gripper is not None:
        frame['gripper'] = float(data.gripper)
    if data.delta is not None:
        frame['delta'] = _to_list(data.delta)
    if data.axes:
        frame['axes'] = {k: float(v) for k, v in data.axes.items()}
    if data.buttons:
        frame['buttons'] = {k: int(v) for k, v in data.buttons.items()}

    if robot_state is not None:
        frame['robot'] = {
            'tcp_pose': _to_list(robot_state.tcp_pose),
            'joints': _to_list(robot_state.joints),
            'gripper_norm': robot_state.gripper_norm,
            'error_code': int(robot_state.error_code),
        }
    return frame


def main():
    parser = argparse.ArgumentParser(description='Collect teleop device data into jsonl')
    parser.add_argument('--teleop-type', type=str, required=True,
                        choices=['pika', 'umi', 'gello', 'xbox', 'spacemouse'],
                        help='teleop device type')
    parser.add_argument('-c', '--config', type=str, required=True,
                        help='teleop config file path, e.g. pika_teleop/config/xarm6_pika_teleop.yaml')
    parser.add_argument('-o', '--output', type=str, required=True,
                        help='output jsonl file path, e.g. data/pika_ep001.jsonl')
    parser.add_argument('--with-robot', action='store_true',
                        help='also connect the robot (from RobotConfig) and record its state without sending actions')
    parser.add_argument('--fps', type=float, default=None,
                        help='sampling rate, defaults to TeleoperatorConfig.fps or 30')
    args = parser.parse_args()

    try:
        with open(Path(args.config).expanduser(), 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print('Error loading config yaml file: {}'.format(e))
        return 1

    if 'TeleoperatorConfig' not in config:
        print('Unsupported config: missing TeleoperatorConfig '
              '(dual-arm configs with L/R keys are not supported)')
        return 1

    teleop_cfg = config['TeleoperatorConfig'] or {}
    fps = args.fps if args.fps is not None else teleop_cfg.get('fps', 30)
    sleep_time = 1.0 / fps

    teleop = build_teleop(args.teleop_type, teleop_cfg)
    teleop.connect()
    print('Teleop device connected: {}'.format(args.teleop_type))

    robot = None
    if args.with_robot:
        if 'RobotConfig' not in config:
            print('RobotConfig is required when --with-robot is set')
            teleop.close()
            return 1
        print('WARNING: UFRobot initialization moves the robot to start_joints, '
              'and no motion commands are sent during collection.')
        from uf_teleop_core.robot import UFRobotConfig, UFRobot
        robot = UFRobot(UFRobotConfig(**config['RobotConfig']))
        print('Robot connected.')

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print('\n********** Teleop Data Collection **********')
    input('Enter to start recording (Ctrl+C to stop) >>> ')

    frame_count = 0
    start_time = None
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            while True:
                time.sleep(sleep_time)
                robot_state = robot.get_state() if robot is not None else None
                data = teleop.get_data()
                if data is None:
                    continue
                if start_time is None:
                    start_time = data.timestamp
                f.write(json.dumps(frame_to_dict(data, robot_state), ensure_ascii=False) + '\n')
                frame_count += 1
    except KeyboardInterrupt:
        print('\nRecording stopped.')
    finally:
        teleop.close()
        if robot is not None:
            robot.close()

    duration = time.monotonic() - start_time if start_time is not None else 0.0
    print('Saved {} frames ({:.2f}s) to {}'.format(frame_count, duration, output_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
