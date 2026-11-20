#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""独立使用 Teleop 设备（可选叠加 Robot 状态）进行数据采集。

输出为 v2 JSONL 格式（首行是文件级 meta，后续每行一帧）：

    {"type": "meta", "version": 2, "teleop_type": "gello", "space": "joint",
     "fps": 30.0, "t0_us": 123..., "units": {...}}
    {"t_us": 0, "joints": [...], "gripper": 0.0}
    {"t_us": 33588, "joints": [...], "gripper": 0.0}

- `space` 只在 meta 中出现，不再每帧重复；
- 帧时间 `t_us` 为相对 meta `t0_us` 的微秒数；
- 默认跳过无效帧（如 Pika 丢追踪），`--keep-invalid` 时写稀疏的
  `{"t_us": ..., "valid": false}`；
- xbox/spacemouse 的原始轴值默认不记录，`--include-axes` 时写入；
- 输出路径以 `.gz` 结尾时自动 gzip 压缩。

示例:
    python scripts/collect_data.py --teleop-type pika \
        -c pika_teleop/config/xarm6_pika_teleop.yaml -o data/pika_ep001.jsonl

默认只连接遥操作设备；--with-robot 时额外连接机械臂并记录其状态
（注意: UFRobot 初始化会移动机械臂到 start_joints，采集中不发送动作）。

运行前需在仓库根目录安装核心库，例如 `pip install -e ".[pika]"`（按设备选择 extra）。
"""

import sys
import gzip
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from uf_teleop_core.config import load_config
from uf_teleop_core.teleop.pika_teleop_device import PikaTeleopDevice
from uf_teleop_core.teleop.umi_teleop_device import UmiTeleopDevice
from uf_teleop_core.teleop.gello_teleop_device import GelloTeleopDevice
from uf_teleop_core.teleop.xbox_teleop_device import XboxTeleopDevice
from uf_teleop_core.teleop.spacemouse_teleop_device import SpacemouseTeleopDevice

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('collect_data')

DEFAULT_GELLO_JOINTS = (1, 2, 3, 4, 5, 6, 7)
FORMAT_VERSION = 2

TELEOP_SPACES = {
    'pika': 'cartesian',
    'umi': 'cartesian',
    'gello': 'joint',
    'xbox': 'cartesian_delta',
    'spacemouse': 'cartesian_delta',
}


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


def _round_list(value, ndigits):
    if value is None:
        return None
    return np.asarray(value, dtype=float).reshape(-1).round(ndigits).tolist()


def make_meta(teleop_type, fps, t0_us, config_path, robot_included, axes_included, keep_invalid):
    """Build the v2 file-level metadata line."""
    return {
        'type': 'meta',
        'version': FORMAT_VERSION,
        'teleop_type': teleop_type,
        'space': TELEOP_SPACES[teleop_type],
        'fps': float(fps),
        't0_us': int(t0_us),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'config_file': str(config_path),
        'robot_included': bool(robot_included),
        'axes_included': bool(axes_included),
        'keep_invalid': bool(keep_invalid),
        'units': {
            'position': 'm',
            'quaternion': 'xyzw',
            'joints': 'rad',
            'gripper': '0_open_1_closed',
            'delta': 'mm_deg_rpy',
            'robot_tcp_pose': 'mm_rad',
            'robot_joints': 'rad',
        },
    }


def frame_to_dict(data, t0_us, include_axes=False, robot_state=None):
    """Serialize one TeleopData frame for the v2 format."""
    frame = {'t_us': max(0, int(round((data.timestamp - t0_us / 1e6) * 1e6)))}
    if not data.valid:
        frame['valid'] = False
        return frame

    if data.position is not None:
        frame['position'] = _round_list(data.position, 6)
    if data.quaternion is not None:
        frame['quaternion'] = _round_list(data.quaternion, 6)
    if data.joints is not None:
        frame['joints'] = _round_list(data.joints, 6)
    if data.gripper is not None:
        frame['gripper'] = round(float(data.gripper), 4)
    if data.delta is not None:
        frame['delta'] = _round_list(data.delta, 4)
    if include_axes and data.axes:
        frame['axes'] = {k: round(float(v), 4) for k, v in data.axes.items()}
    if data.buttons:
        frame['buttons'] = {k: int(v) for k, v in data.buttons.items()}

    if robot_state is not None:
        robot = {}
        if robot_state.tcp_pose is not None:
            robot['tcp_pose'] = _round_list(robot_state.tcp_pose, 6)
        if robot_state.joints is not None:
            robot['joints'] = _round_list(robot_state.joints, 6)
        if robot_state.gripper_norm is not None:
            robot['gripper_norm'] = round(float(robot_state.gripper_norm), 4)
        if robot_state.error_code:
            robot['error_code'] = int(robot_state.error_code)
        if robot:
            frame['robot'] = robot
    return frame


def main():
    parser = argparse.ArgumentParser(description='Collect teleop device data into v2 jsonl')
    parser.add_argument('--teleop-type', type=str, required=True,
                        choices=['pika', 'umi', 'gello', 'xbox', 'spacemouse'],
                        help='teleop device type')
    parser.add_argument('-c', '--config', type=str, required=True,
                        help='teleop config file path, e.g. pika_teleop/config/xarm6_pika_teleop.yaml')
    parser.add_argument('-o', '--output', type=str, required=True,
                        help='output jsonl file path; .gz suffix enables gzip')
    parser.add_argument('--with-robot', action='store_true',
                        help='also connect the robot (from RobotConfig) and record its state without sending actions')
    parser.add_argument('--fps', type=float, default=None,
                        help='sampling rate, defaults to TeleoperatorConfig.fps or 30')
    parser.add_argument('--include-axes', action='store_true',
                        help='record raw device axes (xbox/spacemouse); off by default')
    parser.add_argument('--keep-invalid', action='store_true',
                        help='write sparse {t_us, valid: false} frames instead of skipping them')
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print('Error loading config yaml file: {}'.format(e))
        return 1

    if 'TeleoperatorConfig' not in config:
        print('Unsupported config: missing TeleoperatorConfig '
              '(dual-arm configs with L/R keys are not supported)')
        return 1

    teleop_cfg = config['TeleoperatorConfig'] or {}
    fps = args.fps if args.fps is not None else teleop_cfg.get('fps', 30)
    if fps <= 0:
        print('--fps must be > 0')
        return 1
    sleep_time = 1.0 / fps
    expected_space = TELEOP_SPACES[args.teleop_type]

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
    open_file = gzip.open if output_path.suffix == '.gz' else open

    print('\n********** Teleop Data Collection (v2) **********')
    input('Enter to start recording (Ctrl+C to stop) >>> ')

    frame_count = 0
    t0_us = int(time.monotonic() * 1e6)
    meta = make_meta(args.teleop_type, fps, t0_us, args.config,
                     robot is not None, args.include_axes, args.keep_invalid)
    try:
        with open_file(output_path, 'wt', encoding='utf-8') as f:
            f.write(json.dumps(meta, ensure_ascii=False) + '\n')
            while True:
                time.sleep(sleep_time)
                robot_state = robot.get_state() if robot is not None else None
                data = teleop.get_data()
                if data is None:
                    continue
                if data.space.value != expected_space:
                    print('Teleop device reported space {} but expected {}; stopping'.format(
                        data.space.value, expected_space))
                    break
                if not data.valid and not args.keep_invalid:
                    continue
                f.write(json.dumps(frame_to_dict(data, t0_us, args.include_axes, robot_state),
                                   ensure_ascii=False) + '\n')
                frame_count += 1
    except KeyboardInterrupt:
        print('\nRecording stopped.')
    finally:
        teleop.close()
        if robot is not None:
            robot.close()

    duration = time.monotonic() - t0_us / 1e6
    print('Saved {} frames ({:.2f}s) to {}'.format(frame_count, duration, output_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
