import time
import logging
from typing import Optional

import numpy as np

from .base import TeleopData, TeleopDevice, TeleopSpace

logger = logging.getLogger('uf.teleop.spacemouse')


class SpacemouseTeleopDevice(TeleopDevice):
    """3Dconnexion SpaceMouse 遥操作设备（增量型）。

    数据: delta = [dx, dy, dz, drx, dry, drz] (mm, deg)，
    由六轴输入按 direction、max_distances 映射得到；buttons 为左右键。
    """

    def __init__(self, axes_deadzone=(0.15, 0.15, 0.10, 0.15, 0.15, 0.10),
                 max_distances=(500, 500, 500, 60, 60, 60), direction=0):
        self._axes_deadzone = axes_deadzone
        self._max_distances = max_distances
        self._direction = direction
        self._spacemouse = None

    @property
    def connected(self) -> bool:
        return self._spacemouse is not None and self._spacemouse.connected

    def connect(self):
        if self._spacemouse is not None:
            return
        from uf_teleop_core.devices.spacemouse import SpaceDevice
        self._spacemouse = SpaceDevice(axes_deadzone=list(self._axes_deadzone), logger=logger)
        self._spacemouse.start()

    def close(self):
        if self._spacemouse is not None:
            self._spacemouse.close()
            self._spacemouse = None

    def get_data(self) -> Optional[TeleopData]:
        if not self.connected:
            return None

        state = self._spacemouse.state
        if len(state.buttons) < 2:
            return None

        d = self._max_distances
        delta = np.zeros(6)

        if self._direction == 180:
            delta[0] = -state.y * d[0]
            delta[1] = state.x * d[1]
            delta[2] = state.z * d[2]
            delta[3] = -state.roll * d[3]
            delta[4] = -state.pitch * d[4]
            delta[5] = -state.yaw * d[5]
        elif self._direction == 90:
            delta[0] = -state.x * d[0]
            delta[1] = -state.y * d[1]
            delta[2] = state.z * d[2]
            delta[3] = state.pitch * d[3]
            delta[4] = -state.roll * d[4]
            delta[5] = -state.yaw * d[5]
        elif self._direction == 270:
            delta[0] = state.x * d[0]
            delta[1] = state.y * d[1]
            delta[2] = state.z * d[2]
            delta[3] = -state.pitch * d[3]
            delta[4] = state.roll * d[4]
            delta[5] = -state.yaw * d[5]
        else:
            delta[0] = state.y * d[0]
            delta[1] = -state.x * d[1]
            delta[2] = state.z * d[2]
            delta[3] = state.roll * d[3]
            delta[4] = state.pitch * d[4]
            delta[5] = -state.yaw * d[5]

        return TeleopData(
            timestamp=time.monotonic(),
            space=TeleopSpace.CARTESIAN_DELTA,
            delta=delta,
            axes={
                'x': state.x,
                'y': state.y,
                'z': state.z,
                'roll': state.roll,
                'pitch': state.pitch,
                'yaw': state.yaw,
            },
            buttons={
                'LEFT': int(state.buttons[0]),
                'RIGHT': int(state.buttons[1]),
            },
        )
