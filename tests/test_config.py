import math

import pytest

from uf_teleop_core.config import load_config


def _write(tmp_path, text, name='config.yaml'):
    path = tmp_path / name
    path.write_text(text, encoding='utf-8')
    return path


DEG_CONFIG = """
angle_unit: deg
RobotConfig:
  start_joints: [0, -30, 90]
  start_tcp_pose: [300, 0, 250, 180, -90, 0]
TeleoperatorConfig:
  start_joints: [0, -90, 45]
  tracker_to_robot_eef: [0, 0, 0, 180, -90, 0]
  robot_base_pose: [350, 0, 250, -90, 0, -90]
"""

RAD_CONFIG = """
angle_unit: rad
RobotConfig:
  robot_mode: 6
  robot_speed: 1.5707963267948966
  robot_acc: 8.726646259971648
  start_joints: [0, -0.5235987755982988]
TeleoperatorConfig:
  max_distances: [500, 500, 500, 1.0471975511965976, 1.0471975511965976, 1.0471975511965976]
  leveling_speed: 0.7853981633974483
  homing_speed: 0.7853981633974483
"""


def test_degrees_are_converted_to_radians(tmp_path):
    config = load_config(_write(tmp_path, DEG_CONFIG))
    assert config['angle_unit'] == 'deg'
    assert config['RobotConfig']['start_joints'] == [0, math.radians(-30), math.radians(90)]
    assert config['RobotConfig']['start_tcp_pose'][:3] == [300, 0, 250]
    assert config['RobotConfig']['start_tcp_pose'][3:] == [math.radians(v) for v in (180, -90, 0)]
    assert config['TeleoperatorConfig']['start_joints'] == [0, math.radians(-90), math.radians(45)]
    assert config['TeleoperatorConfig']['tracker_to_robot_eef'][3:] == [math.radians(v) for v in (180, -90, 0)]
    assert config['TeleoperatorConfig']['robot_base_pose'][:3] == [350, 0, 250]
    assert config['TeleoperatorConfig']['robot_base_pose'][3:] == [math.radians(v) for v in (-90, 0, -90)]


def test_rad_pose_fields_pass_through(tmp_path):
    config = load_config(_write(tmp_path, RAD_CONFIG))
    assert config['angle_unit'] == 'rad'
    assert config['RobotConfig']['start_joints'] == [0, -0.5235987755982988]


def test_rad_config_normalizes_degree_consumers(tmp_path):
    config = load_config(_write(tmp_path, RAD_CONFIG))
    assert config['RobotConfig']['robot_speed'] == pytest.approx(90.0)
    assert config['RobotConfig']['robot_acc'] == pytest.approx(500.0)
    assert config['TeleoperatorConfig']['max_distances'][:3] == [500, 500, 500]
    assert config['TeleoperatorConfig']['max_distances'][3:] == pytest.approx([60, 60, 60])
    assert config['TeleoperatorConfig']['leveling_speed'] == pytest.approx(45.0)
    assert config['TeleoperatorConfig']['homing_speed'] == pytest.approx(45.0)


def test_rad_cartesian_speed_is_not_converted(tmp_path):
    text = RAD_CONFIG.replace('robot_mode: 6', 'robot_mode: 7')
    config = load_config(_write(tmp_path, text))
    assert config['RobotConfig']['robot_speed'] == 1.5707963267948966
    assert config['RobotConfig']['robot_acc'] == 8.726646259971648


def test_missing_unit_keeps_legacy_mixed_units(tmp_path):
    text = RAD_CONFIG.replace('angle_unit: rad\n', '')
    path = _write(tmp_path, text)
    with pytest.warns(RuntimeWarning, match='angle_unit'):
        config = load_config(path)
    assert config['angle_unit'] == 'rad'
    # Legacy behavior: poses are radians, other angular fields stay in degrees.
    assert config['RobotConfig']['start_joints'] == [0, -0.5235987755982988]
    assert config['RobotConfig']['robot_speed'] == 1.5707963267948966
    assert config['TeleoperatorConfig']['max_distances'][3] == 1.0471975511965976
    assert config['TeleoperatorConfig']['leveling_speed'] == 0.7853981633974483


def test_dual_arm_sections(tmp_path):
    text = """
angle_unit: deg
L:
  RobotConfig:
    start_joints: [0, -13, -24, -180, 54, -90]
    start_tcp_pose: [350, 0, 250, -90, 0, -90]
  TeleoperatorConfig:
    tracker_to_robot_eef: [0, 0, 0, 0, 0, -90]
    robot_base_pose: [350, 0, 250, -90, 0, -90]
R:
  RobotConfig:
    start_joints: [0, -13, -24, -180, 54, -90]
"""
    config = load_config(_write(tmp_path, text))
    assert config['L']['RobotConfig']['start_joints'][3] == math.radians(-180)
    assert config['L']['TeleoperatorConfig']['tracker_to_robot_eef'][5] == math.radians(-90)
    assert config['R']['RobotConfig']['start_joints'][5] == math.radians(-90)


def test_degree_config_keeps_degree_consumers(tmp_path):
    text = """
angle_unit: deg
RobotConfig:
  robot_mode: 6
  robot_speed: 90
  robot_acc: 500
TeleoperatorConfig:
  max_distances: [500, 500, 500, 60, 60, 60]
  leveling_speed: 45
  homing_speed: 45
"""
    config = load_config(_write(tmp_path, text))
    assert config['RobotConfig']['robot_speed'] == 90
    assert config['RobotConfig']['robot_acc'] == 500
    assert config['TeleoperatorConfig']['max_distances'] == [500, 500, 500, 60, 60, 60]
    assert config['TeleoperatorConfig']['leveling_speed'] == 45
    assert config['TeleoperatorConfig']['homing_speed'] == 45


def test_invalid_unit_is_rejected(tmp_path):
    text = DEG_CONFIG.replace('angle_unit: deg', 'angle_unit: turn')
    with pytest.raises(ValueError, match='angle_unit'):
        load_config(_write(tmp_path, text))
