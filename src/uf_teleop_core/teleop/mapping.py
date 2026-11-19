from typing import Optional

import numpy as np

from uf_teleop_core.transformations import Transformations
from .base import TeleopData, TeleopSpace


class CartesianTeleopMapper:
    """将笛卡尔遥操作位姿映射为机器人目标位姿。

    映射公式（与旧入口保持一致）:
        机械臂目标 = 机械臂初始位姿 * inv(遥操作初始位姿) * 当前遥操作位姿

    - teleop position 单位为米，内部换算为毫米。
    - 输出 [x, y, z, rx, ry, rz] (mm, rad)，默认轴角表示。
    """

    def __init__(self, tracker_to_robot_eef, robot_base_pose=None, is_axis_angle=True):
        self._is_axis_angle = is_axis_angle
        self._tracker_to_robot_matrix = Transformations.xyzrpy_to_rotation_matrix(*tracker_to_robot_eef)
        self._robot_base_matrix = None
        if robot_base_pose is not None:
            self._robot_base_matrix = Transformations.xyzrpy_to_rotation_matrix(*robot_base_pose)
        self._begin_tracker_robot_matrix = None

    @property
    def initialized(self) -> bool:
        return self._begin_tracker_robot_matrix is not None

    def reset(self, data: TeleopData, robot_tcp_pose=None):
        """以当前遥操作位姿为起点初始化映射。

        robot_tcp_pose: [x, y, z, roll, pitch, yaw] (mm, rad)。
        构造时已提供 robot_base_pose 时忽略该参数。
        """
        if data is None or not data.valid or data.space != TeleopSpace.CARTESIAN:
            raise ValueError('Cannot reset mapper with invalid cartesian teleop data')
        if self._robot_base_matrix is None:
            if robot_tcp_pose is None:
                raise ValueError('robot_tcp_pose is required when robot_base_pose is not configured')
            self._robot_base_matrix = Transformations.xyzrpy_to_rotation_matrix(*robot_tcp_pose)
        self._begin_tracker_robot_matrix = self._pose_to_matrix(data)

    def map(self, data: TeleopData) -> Optional[list]:
        """返回机器人目标位姿；未初始化或数据无效时返回 None。"""
        if self._begin_tracker_robot_matrix is None or data is None or not data.valid or data.space != TeleopSpace.CARTESIAN:
            return None
        end_matrix = self._pose_to_matrix(data)
        return Transformations.tracker_robot_matrix_to_robot_pose(
            self._begin_tracker_robot_matrix,
            end_matrix,
            self._robot_base_matrix,
            is_axis_angle=self._is_axis_angle,
        )

    def _pose_to_matrix(self, data: TeleopData) -> np.ndarray:
        position = np.asarray(data.position, dtype=float).reshape(-1) * 1000.0
        x, y, z = position[:3]
        return Transformations.tracker_pose_to_robot_matrix(
            x, y, z, data.quaternion, self._tracker_to_robot_matrix
        )
