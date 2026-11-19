import time
import logging
from typing import Optional

import numpy as np

from uf_teleop_core.devices.pika import PikaDevice
from .base import TeleopData, TeleopDevice, TeleopSpace

logger = logging.getLogger('uf.teleop.pika')


class PikaTeleopDevice(TeleopDevice):
    """Pika Sense 遥操作设备。

    数据: Vive Tracker 位姿 (m, 四元数 xyzw)、夹爪归一化值、command 按键状态。
    底层对象通过 pika_device / pika_sense 暴露，便于采集原始数据。
    """

    def __init__(self, pika_sense_port=None, vive_tracker_id=None,
                 use_gripper=True, gripper_deadband=2.0):
        self._pika_sense_port = pika_sense_port
        self._configured_tracker_id = vive_tracker_id
        self._use_gripper = use_gripper
        self._gripper_deadband = gripper_deadband

        self.pika_device = None
        self.pika_sense = None
        self.vive_tracker_id = None

        self._last_gripper_distance = 0.0
        self._gripper_norm = 0.0

    def connect(self):
        if self.pika_sense is not None:
            return
        self.pika_device = PikaDevice(1, pika_sense_port=self._pika_sense_port)
        self.pika_sense = self.pika_device.pika_sense
        self.vive_tracker_id = (
            self.pika_device.pika_tracker_device
            if self._configured_tracker_id is None
            else self._configured_tracker_id
        )
        logger.info('Pika teleop device ready, tracker: {}'.format(self.vive_tracker_id))

    def close(self):
        if self.pika_sense is None and self.pika_device is None:
            return
        sense = self.pika_sense
        pika_device = self.pika_device
        self.pika_sense = None
        self.vive_tracker_id = None
        self.pika_device = None
        if pika_device is not None:
            port = getattr(pika_device, '_pika_sense_port', None)
            if port is not None and PikaDevice.PIKA_DEVICE_MAP.get(port) is sense:
                PikaDevice.PIKA_DEVICE_MAP.pop(port, None)
            # 避免 PikaDevice.__del__ 重复断开
            pika_device._pika_sense = None
        if sense is not None:
            try:
                sense.disconnect()
            except Exception as e:
                logger.debug('Pika Sense disconnect error: {}'.format(e))

    def get_command_state(self):
        if self.pika_sense is None:
            return None
        return self.pika_sense.get_command_state()

    def get_data(self) -> Optional[TeleopData]:
        if self.pika_sense is None:
            return None

        data = TeleopData(
            timestamp=time.monotonic(),
            space=TeleopSpace.CARTESIAN,
            buttons={'command': self.pika_sense.get_command_state()},
        )

        pose = self.pika_sense.get_pose(self.vive_tracker_id)
        if pose:
            data.position = np.asarray(pose.position, dtype=float)
            data.quaternion = np.asarray(pose.rotation, dtype=float)

        if self._use_gripper:
            distance = self.pika_sense.get_gripper_distance()
            if distance is not None and abs(self._last_gripper_distance - distance) > self._gripper_deadband:
                self._last_gripper_distance = distance
                self._gripper_norm = (100.0 - distance) / 100.0
            data.gripper = self._gripper_norm

        return data
