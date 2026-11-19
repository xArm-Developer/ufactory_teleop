import numpy as np

from uf_teleop_core.transformations import Transformations


def test_quaternion_identity():
    np.testing.assert_allclose(
        Transformations.quaternion_to_rotation_matrix([0, 0, 0, 1]),
        np.eye(3),
        atol=1e-12,
    )


def test_rpy_roundtrip():
    rpy = (0.3, -0.4, 1.2)
    matrix = Transformations.rpy_to_rotation_matrix(*rpy)
    np.testing.assert_allclose(Transformations.rotation_matrix_to_rpy(matrix), rpy, atol=1e-12)


def test_xyzrpy_matrix_roundtrip():
    pose = [300.0, -20.0, 250.0, 0.1, -0.2, 0.5]
    matrix = Transformations.xyzrpy_to_rotation_matrix(*pose)
    np.testing.assert_allclose(Transformations.rotation_matrix_to_xyzrpy(matrix), pose, atol=1e-12)


def test_xyzq_matrix_roundtrip():
    xyz = [0.1, 0.2, 0.3]
    q = np.array([0.1, -0.2, 0.3, 0.9])
    q = q / np.linalg.norm(q)
    matrix = Transformations.xyzq_to_rotation_matrix(*xyz, q)
    result = Transformations.rotation_matrix_to_xyzq(matrix)
    xyz_back, q_back = result[:3], result[3]
    np.testing.assert_allclose(xyz_back, xyz, atol=1e-12)
    np.testing.assert_allclose(np.abs(np.dot(q_back, q)), 1.0, atol=1e-12)
