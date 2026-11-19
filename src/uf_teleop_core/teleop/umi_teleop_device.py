import time
import logging
from typing import Optional

import numpy as np

from .base import TeleopData, TeleopDevice, TeleopSpace

logger = logging.getLogger('uf.teleop.umi')


class UmiTeleopDevice(TeleopDevice):
    """UMI 遥操作设备。

    数据: SLAM 或 Vive Tracker 位姿 (m, 四元数 xyzw) + clamp 夹爪归一化值。
    底层对象通过 xvlib / tracker 暴露，便于采集相机等原始数据。
    """

    def __init__(self, serial_number, use_gripper=True,
                 use_vive_tracker=False, vive_tracker_id='WM0'):
        self._serial_number = serial_number
        self._use_gripper = use_gripper
        self._use_vive_tracker = use_vive_tracker
        self._vive_tracker_id = vive_tracker_id

        self.xvlib = None
        self.tracker = None
        self._gripper_norm = 0.0

    def connect(self):
        if self.xvlib is not None or self.tracker is not None:
            return
        from uf_teleop_core.devices.umi import XVLib

        if self._use_vive_tracker:
            from uf_teleop_core.devices.umi.vive_tracker import ViveTracker
            self.tracker = ViveTracker()
        self.xvlib = XVLib(
            self._serial_number,
            init_slam=not self._use_vive_tracker,
            init_clamp_stream=self._use_gripper,
        )

    def close(self):
        if self.tracker is not None:
            try:
                self.tracker.close()
            except Exception as e:
                logger.debug('ViveTracker close error: {}'.format(e))
            self.tracker = None
        if self.xvlib is not None:
            try:
                self.xvlib.xv_uninit()
            except Exception as e:
                logger.debug('XVLib uninit error: {}'.format(e))
            # 避免 XVLib.__del__ 重复 uninit
            self.xvlib.instance_id = -1
            self.xvlib = None

    def get_data(self) -> Optional[TeleopData]:
        if self.tracker is not None:
            pose_data = self.tracker.get_pose(self._vive_tracker_id)
            if pose_data is None:
                print('cant not get pose from vive tracker')
                return None
            position = pose_data.position.to_list(6)
            quaternion = pose_data.quaternion.to_list(6)
        elif self.xvlib is not None:
            code, pose_data = self.xvlib.xv_get_slam_data()
            if code != 0:
                return None
            position = pose_data.position.to_list(6)
            quaternion = pose_data.quaternion.to_list(6)
        else:
            return None

        data = TeleopData(
            timestamp=time.monotonic(),
            space=TeleopSpace.CARTESIAN,
            position=np.asarray(position, dtype=float),
            quaternion=np.asarray(quaternion, dtype=float),
        )

        if self._use_gripper:
            code, clamp_data = self.xvlib.xv_get_clamp_stream_data()
            if code == 0:
                self._gripper_norm = (87.0 - clamp_data.data) / 87.0
            data.gripper = self._gripper_norm

        return data
