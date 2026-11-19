import time
import logging
from typing import Optional

import numpy as np

from uf_teleop_core.devices.gello import GelloDevice
from .base import TeleopData, TeleopDevice, TeleopSpace

logger = logging.getLogger('uf.teleop.gello')


class GelloTeleopDevice(TeleopDevice):
    """Gello 关节空间遥操作设备。

    数据: 关节角 (rad) + 夹爪归一化值（gripper_id >= 0 时为 act() 的最后一维）。
    connect() 时由 GelloDevice 完成关节零位标定与 GelloAgent 初始化。
    """

    def __init__(self, port=None, joint_ids=(1, 2, 3, 4, 5, 6, 7),
                 joint_signs=(1, 1, 1, 1, 1, 1, 1),
                 start_joints=(0, 0, 0, np.pi / 2, 0, np.pi / 2, 0),
                 gripper_id=8, torque_joint_ids=None):
        self._gripper_id = gripper_id
        self._device = GelloDevice(
            port=port,
            joint_ids=joint_ids,
            joint_signs=joint_signs,
            start_joints=start_joints,
            gripper_id=gripper_id,
            torque_joint_ids=torque_joint_ids,
        )

    @property
    def gello_agent(self):
        """底层 GelloAgent，未连接时为 None。"""
        return self._device.gello_agent

    def connect(self):
        self._device.connect()

    def close(self):
        self._device.close()

    def get_data(self) -> Optional[TeleopData]:
        action = self._device.get_action()
        if action is None:
            return None

        data = TeleopData(
            timestamp=time.monotonic(),
            space=TeleopSpace.JOINT,
        )
        if self._gripper_id >= 0:
            data.joints = action[:-1].copy()
            data.gripper = float(action[-1])
        else:
            data.joints = action.copy()
        return data
