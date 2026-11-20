#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Replay teleop JSONL data (from collect_data.py) on a UFACTORY robot.

Only the v2 recording format is supported: the first line is a meta record that
declares ``space``, ``t0_us`` and ``fps``; frame lines carry relative ``t_us``.

Detected from the recorded ``space`` field:

- ``cartesian`` (pika / umi): absolute teleop pose, mapped with the same
  ``CartesianTeleopMapper`` used by the teleoperation entries. When
  ``TeleoperatorConfig.robot_base_pose`` is set (UMI) it is used as the base;
  otherwise the robot pose at replay start is used (pika).
- ``joint`` (gello): joint positions are sent directly (robot_mode 6).
- ``cartesian_delta`` (xbox / spacemouse): per-frame deltas are integrated
  from the robot pose at replay start. For Xbox data the D-pad z/yaw sign is
  applied from the recorded buttons; the single-click Z/YAW reversal toggle
  is not part of the recorded data and is therefore not reproduced.

Examples:
    # preview without touching the robot
    python scripts/replay_data.py -i data/pika_ep001.jsonl \
        -c pika_teleop/config/xarm6_pika_teleop.yaml --dry-run

    # replay at half speed
    python scripts/replay_data.py -i data/umi_ep001.jsonl \
        -c umi_teleop/config/xarm6_umi_teleop.yaml --speed 0.5
"""

import sys
import gzip
import json
import time
import argparse
from pathlib import Path

import numpy as np

from uf_teleop_core.config import load_config
from uf_teleop_core.teleop import CartesianTeleopMapper, TeleopData, TeleopSpace
from uf_teleop_core.transformations import Transformations

DEFAULT_FPS = 30.0
DEFAULT_MAX_DT = 1.0


def _open_text(path):
    path = Path(path).expanduser()
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8')
    return open(path, 'r', encoding='utf-8')


def load_recording(path):
    """Load a v2 recording and return (meta, frames).

    Frames are normalized with a reconstructed absolute ``timestamp`` and the
    file-level ``space`` injected, so the rest of the replay code is unchanged.
    """
    with _open_text(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        raise ValueError('No data found in {}'.format(path))

    try:
        meta = json.loads(lines[0])
    except json.JSONDecodeError as e:
        raise ValueError('{}:1: invalid JSON: {}'.format(path, e))
    if meta.get('type') != 'meta' or int(meta.get('version', 0)) != 2:
        raise ValueError('{}: unsupported format; expected a v2 meta line '
                         '(re-collect with the v2 collector)'.format(path))
    space = meta.get('space')
    if space not in {item.value for item in TeleopSpace}:
        raise ValueError('{}: invalid space in meta: {!r}'.format(path, space))

    t0_us = int(meta.get('t0_us', 0))
    frames = []
    for lineno, line in enumerate(lines[1:], 2):
        try:
            frame = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError('{}:{}: invalid JSON: {}'.format(path, lineno, e))
        frame.setdefault('valid', True)
        frame['space'] = space
        frame['timestamp'] = (t0_us + int(frame.get('t_us', 0))) / 1e6
        frames.append(frame)
    if not frames:
        raise ValueError('No frames found in {}'.format(path))
    return meta, frames


def to_teleop_data(frame):
    """Rebuild TeleopData from a recorded jsonl frame."""
    def _array(key):
        value = frame.get(key)
        return None if value is None else np.asarray(value, dtype=float)

    return TeleopData(
        timestamp=float(frame.get('timestamp', 0.0)),
        space=TeleopSpace(frame['space']),
        position=_array('position'),
        quaternion=_array('quaternion'),
        joints=_array('joints'),
        gripper=float(frame['gripper']) if frame.get('gripper') is not None else None,
        buttons={k: int(v) for k, v in frame.get('buttons', {}).items()},
        delta=_array('delta'),
        axes={k: float(v) for k, v in frame.get('axes', {}).items()},
    )


class ActionBuilder(object):
    """Turn recorded TeleopData frames into UFRobot.send_action() arrays."""

    def __init__(self, space, teleop_cfg, robot_pose=None):
        self.space = space
        self._robot_pose = robot_pose
        self._mapper = None
        self._base_pose = None
        self._delta_sum = np.zeros(6)

        if space == TeleopSpace.CARTESIAN:
            if 'tracker_to_robot_eef' not in teleop_cfg:
                raise ValueError('TeleoperatorConfig.tracker_to_robot_eef is required for cartesian replay')
            self._mapper = CartesianTeleopMapper(
                teleop_cfg['tracker_to_robot_eef'],
                robot_base_pose=teleop_cfg.get('robot_base_pose'),
            )
        elif space == TeleopSpace.CARTESIAN_DELTA:
            pose = (0.0,) * 6 if robot_pose is None else robot_pose
            self._base_pose = np.asarray(pose, dtype=float)
        elif space != TeleopSpace.JOINT:
            raise ValueError('Unsupported teleop space: {}'.format(space))

    def action(self, data):
        if self.space == TeleopSpace.CARTESIAN:
            if not self._mapper.initialized:
                # dry-run has no robot; use a zero pose for relative mapping
                self._mapper.reset(data, self._robot_pose if self._robot_pose is not None else [0.0] * 6)
            pose = self._mapper.map(data)
            if pose is None:
                return None
            action = list(pose)
        elif self.space == TeleopSpace.JOINT:
            if data.joints is None:
                return None
            action = [float(v) for v in data.joints]
        else:
            if data.delta is None:
                return None
            delta = np.asarray(data.delta, dtype=float).reshape(-1)[:6].copy()
            # Xbox D-pad Z/YAW sign (matches the entry's delta mapping).
            if data.buttons.get('DPAD_Y') == 1:
                delta[2] *= -1.0
                delta[5] *= -1.0
            # Delta rotations are recorded in degrees (the entries feed them to
            # xArm set_position, whose default unit is degrees); the robot pose
            # read via UFRobot.get_position() is in radians.
            delta[3:] = np.deg2rad(delta[3:])
            self._delta_sum += delta
            target_rpy = self._base_pose + self._delta_sum
            matrix = Transformations.xyzrpy_to_rotation_matrix(*target_rpy)
            action = list(Transformations.rotation_matrix_to_xyzrxryrz(matrix))

        if data.gripper is not None:
            action.append(float(data.gripper))
        return action


def _timestamps_usable(frames):
    if len(frames) < 2:
        return False
    stamps = [float(f.get('timestamp', 0.0)) for f in frames]
    return all(t > 0 for t in stamps) and all(stamps[i] > stamps[i - 1] for i in range(1, len(stamps)))


def iter_timed_frames(frames, fps, speed, max_dt):
    """Yield (frame, sleep_seconds) following recorded timing or a fixed FPS."""
    previous = None
    for frame in frames:
        if fps is not None:
            dt = 1.0 / fps
        elif previous is None:
            dt = 0.0
        else:
            dt = float(frame.get('timestamp', 0.0)) - previous
            dt = min(max(dt, 0.0), max_dt)
        previous = float(frame.get('timestamp', 0.0))
        yield frame, dt / speed


def _format_action(action):
    if action is None:
        return 'None'
    return '[' + ', '.join('{:.4f}'.format(float(v)) for v in action) + ']'


def main():
    parser = argparse.ArgumentParser(
        description='Replay teleop JSONL data on a UFACTORY robot',
        epilog='Xbox Z/YAW reversal toggles are not recorded; only the D-pad sign is replayed.',
    )
    parser.add_argument('-i', '--input', type=str, required=True, help='input jsonl file')
    parser.add_argument('-c', '--config', type=str, required=True,
                        help='teleop config yaml (RobotConfig + TeleoperatorConfig)')
    parser.add_argument('--fps', type=float, default=None,
                        help='fixed replay rate; default follows recorded timestamps')
    parser.add_argument('--speed', type=float, default=1.0, help='time scale (>0, 2 = twice as fast)')
    parser.add_argument('--start', type=int, default=0, help='first valid frame index (default 0)')
    parser.add_argument('--end', type=int, default=None, help='exclusive end frame index')
    parser.add_argument('--max-dt', type=float, default=DEFAULT_MAX_DT,
                        help='maximum gap between frames in seconds (default 1.0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='build and print the actions without connecting the robot')
    args = parser.parse_args()

    if args.speed <= 0:
        print('--speed must be > 0')
        return 1
    if args.fps is not None and args.fps <= 0:
        print('--fps must be > 0')
        return 1

    try:
        config = load_config(args.config)
        meta, frames = load_recording(args.input)
    except Exception as e:
        print('Error: {}'.format(e))
        return 1

    valid_frames = [f for f in frames if f.get('valid', True)]
    if not valid_frames:
        print('No valid frames found in {}'.format(args.input))
        return 1

    space = TeleopSpace(meta['space'])

    end = len(valid_frames) if args.end is None else args.end
    valid_frames = valid_frames[args.start:end]
    if not valid_frames:
        print('No frames selected after --start/--end')
        return 1

    robot_cfg = config.get('RobotConfig') or {}
    teleop_cfg = config.get('TeleoperatorConfig') or {}
    robot_mode = int(robot_cfg.get('robot_mode', 7))
    if space == TeleopSpace.JOINT and robot_mode != 6:
        print('Joint replay requires RobotConfig.robot_mode: 6 (got {})'.format(robot_mode))
        return 1
    if space != TeleopSpace.JOINT and robot_mode == 6:
        print('{} replay requires a Cartesian robot_mode (1 or 7), got 6'.format(space.value))
        return 1
    if space == TeleopSpace.CARTESIAN and 'tracker_to_robot_eef' not in teleop_cfg:
        print('TeleoperatorConfig.tracker_to_robot_eef is required for cartesian replay')
        return 1
    if not args.dry_run and 'RobotConfig' not in config:
        print('RobotConfig is required for replay (or use --dry-run)')
        return 1

    fps = args.fps
    if fps is None and not _timestamps_usable(valid_frames):
        fps = float(meta.get('fps', DEFAULT_FPS))
        print('Recorded timestamps unusable; replaying at {:.0f} FPS'.format(fps))

    total_dt = sum(dt for _, dt in iter_timed_frames(valid_frames, fps, args.speed, args.max_dt))
    print('Frames: {} (type={}, space={}, estimated duration={:.2f}s)'.format(
        len(valid_frames), meta.get('teleop_type', '?'), space.value, total_dt))

    builder = ActionBuilder(space, teleop_cfg)
    if args.dry_run:
        if space == TeleopSpace.CARTESIAN and not teleop_cfg.get('robot_base_pose'):
            print('Dry run uses a zero robot base pose for relative mapping.')
        actions = []
        for frame, _ in iter_timed_frames(valid_frames, fps, args.speed, args.max_dt):
            action = builder.action(to_teleop_data(frame))
            if action is not None:
                actions.append(action)
        print('Dry run: {} actions built (robot not connected)'.format(len(actions)))
        if actions:
            print('  first: {}'.format(_format_action(actions[0])))
            print('  last : {}'.format(_format_action(actions[-1])))
        return 0

    from uf_teleop_core.robot import UFRobotConfig, UFRobot

    print('WARNING: UFRobot initialization moves the robot to start_joints, then the replay starts.')
    robot = UFRobot(UFRobotConfig(**robot_cfg))
    try:
        input('Enter to start replay (Ctrl+C to stop) >>> ')
        # Read the base pose after confirmation so a manually jogged robot is respected.
        _, robot_pose = robot.get_position()
        builder = ActionBuilder(space, teleop_cfg, robot_pose)

        sent = 0
        try:
            for frame, dt in iter_timed_frames(valid_frames, fps, args.speed, args.max_dt):
                if dt > 0:
                    time.sleep(dt)
                action = builder.action(to_teleop_data(frame))
                if action is None:
                    continue
                code = robot.send_action(action)
                if code != 0:
                    print('Robot returned error code {} after {} actions; stopping'.format(code, sent))
                    break
                sent += 1
        except KeyboardInterrupt:
            print('\nReplay interrupted.')
        finally:
            print('Replayed {} actions.'.format(sent))
    finally:
        robot.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
