"""YAML config loading with explicit angle units.

Config files declare a top-level ``angle_unit`` (``deg`` or ``rad``). The
runtime API (UFRobot, Transformations, TeleopData) uses fixed internal units,
so ``load_config`` normalizes user-facing values at the boundary:

``angle_unit: deg`` — pose angles are degrees; conversion to radians:
- ``RobotConfig.start_joints`` (all values)
- ``RobotConfig.start_tcp_pose[3:6]`` (orientation only; xyz stays mm)
- ``TeleoperatorConfig.start_joints`` (gello)
- ``TeleoperatorConfig.tracker_to_robot_eef[3:6]``
- ``TeleoperatorConfig.robot_base_pose[3:6]``

``angle_unit: rad`` — continuous angular values are radians. In addition to
leaving the pose fields as radians, the loader normalizes fields whose internal
consumers still use degrees:
- ``RobotConfig.robot_speed`` / ``robot_acc`` in ``robot_mode: 6`` -> deg/s
- ``TeleoperatorConfig.max_distances[3:6]`` -> degrees
- ``TeleoperatorConfig.leveling_speed`` / ``homing_speed`` -> deg/s

Exceptions that never follow ``angle_unit``:
- ``direction`` (discrete 0/90/180/270 degree labels)
- ``robot_speed`` / ``robot_acc`` in Cartesian modes (mm/s, mm/s^2)
- ``TeleopData.delta`` recorded data (always mm/deg)

Configs without ``angle_unit`` keep the legacy mixed behavior (pose fields in
radians, the fields above in degrees) and produce a warning.
"""

import math
import warnings
from pathlib import Path

import yaml


def _convert_orientation(values, converter):
    """Apply ``converter`` to indices 3..5 of an xyzrpy list."""
    result = list(values)
    for index in range(3, min(len(result), 6)):
        result[index] = converter(result[index])
    return result


def _normalize_section(robot_cfg, teleop_cfg, unit, explicit):
    if unit == 'deg':
        if robot_cfg:
            if robot_cfg.get('start_joints') is not None:
                robot_cfg['start_joints'] = [math.radians(v) for v in robot_cfg['start_joints']]
            if robot_cfg.get('start_tcp_pose') is not None:
                robot_cfg['start_tcp_pose'] = _convert_orientation(robot_cfg['start_tcp_pose'], math.radians)
        if teleop_cfg:
            if teleop_cfg.get('start_joints') is not None:
                teleop_cfg['start_joints'] = [math.radians(v) for v in teleop_cfg['start_joints']]
            if teleop_cfg.get('tracker_to_robot_eef') is not None:
                teleop_cfg['tracker_to_robot_eef'] = _convert_orientation(
                    teleop_cfg['tracker_to_robot_eef'], math.radians)
            if teleop_cfg.get('robot_base_pose') is not None:
                teleop_cfg['robot_base_pose'] = _convert_orientation(
                    teleop_cfg['robot_base_pose'], math.radians)
        return

    # unit == 'rad'
    if not explicit:
        # Legacy configs without angle_unit: pose fields are already radians,
        # while max_distances/leveling/homing/joint speeds stay in degrees.
        return

    if robot_cfg:
        if int(robot_cfg.get('robot_mode', 7)) == 6:
            if robot_cfg.get('robot_speed') is not None:
                robot_cfg['robot_speed'] = math.degrees(robot_cfg['robot_speed'])
            if robot_cfg.get('robot_acc') is not None:
                robot_cfg['robot_acc'] = math.degrees(robot_cfg['robot_acc'])
    if teleop_cfg:
        if teleop_cfg.get('max_distances') is not None:
            teleop_cfg['max_distances'] = _convert_orientation(
                teleop_cfg['max_distances'], math.degrees)
        for key in ('leveling_speed', 'homing_speed'):
            if teleop_cfg.get(key) is not None:
                teleop_cfg[key] = math.degrees(teleop_cfg[key])


def _normalize_angle_unit(value):
    unit = str(value).strip().lower()
    if unit in ('deg', 'degree', 'degrees'):
        return 'deg'
    if unit in ('rad', 'radian', 'radians'):
        return 'rad'
    raise ValueError("invalid angle_unit {!r}; use 'deg' or 'rad'".format(value))


def load_config(path):
    """Load a YAML config and normalize its angular fields."""
    path = Path(path).expanduser()
    with open(path, 'r') as f:
        config = yaml.safe_load(f) or {}

    explicit = 'angle_unit' in config
    if not explicit:
        warnings.warn(
            "{}: missing 'angle_unit'; assuming legacy mixed units "
            "(poses in radians, max_distances/leveling/homing in degrees). "
            "Add 'angle_unit: deg' or 'angle_unit: rad' to the config.".format(path),
            RuntimeWarning,
        )
        unit = 'rad'
    else:
        unit = _normalize_angle_unit(config['angle_unit'])
    config['angle_unit'] = unit

    _normalize_section(config.get('RobotConfig'), config.get('TeleoperatorConfig'), unit, explicit)
    for arm in ('L', 'R'):
        section = config.get(arm)
        if isinstance(section, dict):
            _normalize_section(section.get('RobotConfig'), section.get('TeleoperatorConfig'),
                               unit, explicit)
    return config
