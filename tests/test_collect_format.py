import importlib.util
from pathlib import Path

import numpy as np

from uf_teleop_core.robot import RobotState
from uf_teleop_core.teleop import TeleopData, TeleopSpace


def _load_collector():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'collect_data.py'
    spec = importlib.util.spec_from_file_location('collect_data', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect = _load_collector()


def test_teleop_space_mapping():
    assert collect.TELEOP_SPACES == {
        'pika': 'cartesian',
        'umi': 'cartesian',
        'gello': 'joint',
        'xbox': 'cartesian_delta',
        'spacemouse': 'cartesian_delta',
    }


def test_make_meta():
    meta = collect.make_meta('pika', 30, 1234567, 'pika.yaml', True, False, False)
    assert meta['type'] == 'meta'
    assert meta['version'] == 2
    assert meta['teleop_type'] == 'pika'
    assert meta['space'] == 'cartesian'
    assert meta['t0_us'] == 1234567
    assert meta['robot_included'] is True
    assert meta['axes_included'] is False
    assert meta['units']['delta'] == 'mm_deg_rpy'
    assert 'created_at' in meta


def test_cartesian_frame_has_no_space_and_is_rounded():
    data = TeleopData(
        timestamp=1.000123,
        space=TeleopSpace.CARTESIAN,
        position=np.array([0.123456789, 0.0, -0.0]),
        quaternion=np.array([0.0, 0.0, 0.0, 1.0]),
        gripper=0.123456,
    )
    frame = collect.frame_to_dict(data, t0_us=1_000_000)
    assert frame['t_us'] == 123
    assert 'space' not in frame
    assert 'valid' not in frame
    assert frame['position'] == [0.123457, 0.0, 0.0]
    assert frame['gripper'] == 0.1235


def test_invalid_frame_is_sparse():
    data = TeleopData(timestamp=1.0, space=TeleopSpace.CARTESIAN, buttons={'command': 1})
    frame = collect.frame_to_dict(data, t0_us=1_000_000)
    assert frame == {'t_us': 0, 'valid': False}


def test_axes_are_opt_in():
    data = TeleopData(
        timestamp=1.0,
        space=TeleopSpace.CARTESIAN_DELTA,
        delta=np.array([1, 2, 3, 4, 5, 6]),
        axes={'x': 0.123456},
    )
    without = collect.frame_to_dict(data, t0_us=1_000_000)
    assert 'axes' not in without
    with_axes = collect.frame_to_dict(data, t0_us=1_000_000, include_axes=True)
    assert with_axes['axes'] == {'x': 0.1235}
    assert with_axes['delta'] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def test_robot_state_is_optional_and_error_zero_omitted():
    data = TeleopData(
        timestamp=1.0,
        space=TeleopSpace.JOINT,
        joints=np.zeros(6),
    )
    state = RobotState(
        tcp_pose=np.array([300.0, 0.0, 250.0, 0.0, 0.0, 0.0]),
        joints=np.zeros(6),
        gripper_norm=0.5,
        error_code=0,
    )
    frame = collect.frame_to_dict(data, t0_us=1_000_000, robot_state=state)
    assert 'error_code' not in frame['robot']
    assert frame['robot']['gripper_norm'] == 0.5
    assert frame['robot']['tcp_pose'][0] == 300.0
