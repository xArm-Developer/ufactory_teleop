import numpy as np

from uf_teleop_core.teleop import TeleopData, TeleopSpace


def test_cartesian_validity():
    invalid = TeleopData(timestamp=1.0, space=TeleopSpace.CARTESIAN, buttons={'command': 1})
    assert not invalid.valid

    valid = TeleopData(
        timestamp=1.0, space=TeleopSpace.CARTESIAN,
        position=np.zeros(3), quaternion=np.array([0, 0, 0, 1.0]),
    )
    assert valid.valid


def test_delta_validity():
    assert not TeleopData(timestamp=1.0, space=TeleopSpace.CARTESIAN_DELTA).valid
    assert TeleopData(timestamp=1.0, space=TeleopSpace.CARTESIAN_DELTA, delta=np.zeros(6)).valid


def test_joint_validity():
    assert not TeleopData(timestamp=1.0, space=TeleopSpace.JOINT).valid
    assert TeleopData(timestamp=1.0, space=TeleopSpace.JOINT, joints=np.zeros(7)).valid
