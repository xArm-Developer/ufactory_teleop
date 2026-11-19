import numpy as np
import pytest

from uf_teleop_core.teleop import CartesianTeleopMapper, TeleopData, TeleopSpace
from uf_teleop_core.transformations import Transformations as T


def _make_poses(n=5, seed=0):
    rng = np.random.RandomState(seed)
    poses = []
    for _ in range(n):
        position = rng.uniform(-0.5, 0.5, 3)
        quaternion = rng.normal(size=4)
        quaternion /= np.linalg.norm(quaternion)
        poses.append((position, quaternion))
    return poses


def _data(position, quaternion):
    return TeleopData(
        timestamp=0.0,
        space=TeleopSpace.CARTESIAN,
        position=np.asarray(position),
        quaternion=np.asarray(quaternion),
    )


def test_mapper_matches_direct_formula_with_robot_pose():
    eef = [0, 0, 0, np.pi, -np.pi / 2, 0]
    robot_pose = [300.0, 10.0, 250.0, 3.14, 0.0, 0.0]
    mapper = CartesianTeleopMapper(eef)

    eef_matrix = T.xyzrpy_to_rotation_matrix(*eef)
    base_matrix = T.xyzrpy_to_rotation_matrix(*robot_pose)
    begin = None
    for i, (position, quaternion) in enumerate(_make_poses()):
        tracker_matrix = T.tracker_pose_to_robot_matrix(
            position[0] * 1000, position[1] * 1000, position[2] * 1000, quaternion, eef_matrix)
        if i == 0:
            begin = tracker_matrix
            mapper.reset(_data(position, quaternion), robot_pose)
        expected = T.tracker_robot_matrix_to_robot_pose(begin, tracker_matrix, base_matrix, is_axis_angle=True)
        np.testing.assert_allclose(mapper.map(_data(position, quaternion)), expected, atol=1e-12)


def test_mapper_matches_direct_formula_with_configured_base_pose():
    eef = [0, 0, 0, 0, 0, -np.pi / 2]
    base_pose = [350, 0, 250, -1.570796, 0, -1.570796]
    mapper = CartesianTeleopMapper(eef, robot_base_pose=base_pose)

    eef_matrix = T.xyzrpy_to_rotation_matrix(*eef)
    base_matrix = T.xyzrpy_to_rotation_matrix(*base_pose)
    begin = None
    for i, (position, quaternion) in enumerate(_make_poses(seed=1)):
        tracker_matrix = T.tracker_pose_to_robot_matrix(
            position[0] * 1000, position[1] * 1000, position[2] * 1000, quaternion, eef_matrix)
        if i == 0:
            begin = tracker_matrix
            mapper.reset(_data(position, quaternion))
        expected = T.tracker_robot_matrix_to_robot_pose(begin, tracker_matrix, base_matrix, is_axis_angle=True)
        np.testing.assert_allclose(mapper.map(_data(position, quaternion)), expected, atol=1e-12)


def test_mapper_requires_initialization():
    mapper = CartesianTeleopMapper([0, 0, 0, 0, 0, 0])
    data = _data([0.1, 0.2, 0.3], [0, 0, 0, 1])
    assert mapper.map(data) is None
    with pytest.raises(ValueError):
        mapper.reset(data)  # robot_base_pose not configured and robot_tcp_pose missing
