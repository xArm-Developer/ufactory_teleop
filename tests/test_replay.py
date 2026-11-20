import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from uf_teleop_core.teleop import TeleopSpace
from uf_teleop_core.transformations import Transformations


def _load_replay_module():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'replay_data.py'
    spec = importlib.util.spec_from_file_location('replay_data', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


replay = _load_replay_module()


def _meta(space='joint', t0_us=1_000_000, fps=30.0):
    return {'type': 'meta', 'version': 2, 'teleop_type': 'gello', 'space': space,
            'fps': fps, 't0_us': t0_us}


def _frame(space, **fields):
    frame = {'timestamp': 1.0, 'space': space, 'valid': True}
    frame.update(fields)
    return frame


def _write_v2(path, space='joint', frames=None):
    frames = frames or [{'t_us': 0, 'joints': [0] * 7}]
    lines = [json.dumps(_meta(space))] + [json.dumps(f) for f in frames]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def test_load_recording_v2(tmp_path):
    path = tmp_path / 'data.jsonl'
    _write_v2(path, frames=[{'t_us': 0, 'joints': [0] * 7},
                            {'t_us': 20000, 'joints': [1] * 7}])
    meta, frames = replay.load_recording(str(path))
    assert meta['space'] == 'joint'
    assert frames[0]['space'] == 'joint'
    assert frames[0]['valid'] is True
    assert frames[0]['timestamp'] == pytest.approx(1.0)
    assert frames[1]['timestamp'] == pytest.approx(1.02)


def test_load_recording_gzip(tmp_path):
    path = tmp_path / 'data.jsonl.gz'
    lines = [json.dumps(_meta()), json.dumps({'t_us': 0, 'joints': [0] * 7})]
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    meta, frames = replay.load_recording(str(path))
    assert meta['version'] == 2
    assert len(frames) == 1


def test_load_recording_rejects_legacy(tmp_path):
    path = tmp_path / 'legacy.jsonl'
    path.write_text(json.dumps({'timestamp': 1.0, 'space': 'joint', 'valid': True,
                                'joints': [0] * 7}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='v2'):
        replay.load_recording(str(path))


def test_load_recording_invalid_json(tmp_path):
    path = tmp_path / 'bad.jsonl'
    lines = [json.dumps(_meta()), '{not json}']
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        replay.load_recording(str(path))


def test_to_teleop_data_spaces():
    joint = replay.to_teleop_data(_frame('joint', joints=[0, 1, 2, 3, 4, 5], gripper=0.2))
    assert joint.space == TeleopSpace.JOINT
    np.testing.assert_allclose(joint.joints, [0, 1, 2, 3, 4, 5])
    assert joint.gripper == 0.2

    cart = replay.to_teleop_data(_frame('cartesian', position=[0.1, 0.2, 0.3],
                                        quaternion=[0, 0, 0, 1]))
    assert cart.space == TeleopSpace.CARTESIAN
    assert cart.valid

    delta = replay.to_teleop_data(_frame('cartesian_delta', delta=[1] * 6, axes={'x': 0.1},
                                         buttons={'DPAD_Y': -1}))
    assert delta.space == TeleopSpace.CARTESIAN_DELTA
    assert delta.valid
    assert delta.buttons == {'DPAD_Y': -1}


def test_joint_action_builder():
    builder = replay.ActionBuilder(TeleopSpace.JOINT, {})
    data = replay.to_teleop_data(_frame('joint', joints=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6], gripper=0.4))
    action = builder.action(data)
    np.testing.assert_allclose(action, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.4])


def test_cartesian_action_builder():
    cfg = {'tracker_to_robot_eef': [0, 0, 0, 0, 0, 0],
           'robot_base_pose': [300, 0, 250, 0, 0, 0]}
    builder = replay.ActionBuilder(TeleopSpace.CARTESIAN, cfg)

    first = builder.action(replay.to_teleop_data(_frame(
        'cartesian', position=[0.0, 0.0, 0.0], quaternion=[0, 0, 0, 1], gripper=0.1)))
    np.testing.assert_allclose(first, [300, 0, 250, 0, 0, 0, 0.1], atol=1e-9)

    second = builder.action(replay.to_teleop_data(_frame(
        'cartesian', position=[0.01, 0.0, 0.0], quaternion=[0, 0, 0, 1])))
    np.testing.assert_allclose(second[:3], [310, 0, 250], atol=1e-6)
    assert len(second) == 6


def test_delta_action_builder_accumulates():
    builder = replay.ActionBuilder(TeleopSpace.CARTESIAN_DELTA, {}, robot_pose=[300, 0, 250, 0, 0, 0])

    builder.action(replay.to_teleop_data(_frame('cartesian_delta', delta=[10, 0, 0, 0, 0, 0])))
    action = builder.action(replay.to_teleop_data(_frame('cartesian_delta', delta=[5, 0, 0, 0, 0, 0])))
    rpy = Transformations.rotation_matrix_to_xyzrpy(
        Transformations.xyzrxryrz_to_rotation_matrix(*action[:6]))
    np.testing.assert_allclose(rpy, [315, 0, 250, 0, 0, 0], atol=1e-9)


def test_delta_action_builder_applies_dpad_sign():
    builder = replay.ActionBuilder(TeleopSpace.CARTESIAN_DELTA, {}, robot_pose=[300, 0, 250, 0, 0, 0])
    action = builder.action(replay.to_teleop_data(_frame(
        'cartesian_delta', delta=[0, 0, 10, 0, 0, 10], buttons={'DPAD_Y': 1})))
    rpy = Transformations.rotation_matrix_to_xyzrpy(
        Transformations.xyzrxryrz_to_rotation_matrix(*action[:6]))
    np.testing.assert_allclose(rpy, [300, 0, 240, 0, 0, np.deg2rad(-10)], atol=1e-9)


def test_delta_action_builder_converts_degrees_to_radians():
    builder = replay.ActionBuilder(TeleopSpace.CARTESIAN_DELTA, {}, robot_pose=[0, 0, 0, 0, 0, 0])
    action = builder.action(replay.to_teleop_data(_frame('cartesian_delta', delta=[0, 0, 0, 0, 0, 30])))
    rpy = Transformations.rotation_matrix_to_xyzrpy(
        Transformations.xyzrxryrz_to_rotation_matrix(*action[:6]))
    np.testing.assert_allclose(rpy, [0, 0, 0, 0, 0, np.deg2rad(30)], atol=1e-9)
