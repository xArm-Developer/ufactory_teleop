import time
import logging
from typing import Optional

import numpy as np

from .base import TeleopData, TeleopDevice, TeleopSpace

logger = logging.getLogger('uf.teleop.xbox')


class XboxTeleopDevice(TeleopDevice):
    """Xbox 手柄遥操作设备（增量型）。

    数据: delta = [dx, dy, dz, drx, dry, drz] (mm, deg)，
    由摇杆/扳机轴按 direction、max_distances 与 A/B/X/Y 轴锁定规则映射得到。
    dz / drz 的方向（方向键 / 上层反转开关）由调用方处理。
    """

    def __init__(self, axes_deadzone=(0.15, 0.15, 0.1, 0.2, 0.2, 0.1),
                 max_distances=(500, 500, 500, 60, 60, 60), direction=0):
        self._axes_deadzone = axes_deadzone
        self._max_distances = max_distances
        self._direction = direction
        self._xbox = None

    @property
    def connected(self) -> bool:
        return self._xbox is not None and self._xbox.connected

    def connect(self):
        if self._xbox is not None:
            return
        from uf_teleop_core.devices.xbox import XBoxDevice
        self._xbox = XBoxDevice(axes_deadzone=list(self._axes_deadzone), logger=logger)
        self._xbox.start()

    def close(self):
        # XBoxDevice 为 daemon 线程且未提供停止接口，释放引用即可
        self._xbox = None

    def get_data(self) -> Optional[TeleopData]:
        if not self.connected:
            return None

        xbox = self._xbox
        axes = xbox.axes
        buttons = xbox.buttons
        d = self._max_distances
        delta = np.zeros(6)

        # A/B/X/Y 轴锁定规则（与入口原有逻辑一致）
        x_zero = False
        y_zero = False
        dx_zero = False
        dy_zero = False
        if buttons.X.value == 1 or buttons.Y.value == 1:
            x_zero = False if buttons.X.value == 1 else True
            y_zero = False if buttons.Y.value == 1 else True
            dx_zero = True
            dy_zero = True
        elif buttons.A.value == 1 or buttons.B.value == 1:
            x_zero = True
            y_zero = True
            dx_zero = False if buttons.A.value == 1 else True
            dy_zero = False if buttons.B.value == 1 else True

        if self._direction == 180:
            delta[0] = -axes.Y.value * d[0] if not x_zero else 0
            delta[1] = axes.X.value * d[1] if not y_zero else 0
            delta[3] = -axes.RX.value * d[3] if not dx_zero else 0
            delta[4] = -axes.RY.value * d[4] if not dy_zero else 0
        elif self._direction == 90:
            delta[0] = -axes.X.value * d[0] if not x_zero else 0
            delta[1] = -axes.Y.value * d[1] if not y_zero else 0
            delta[3] = axes.RY.value * d[3] if not dx_zero else 0
            delta[4] = -axes.RX.value * d[4] if not dy_zero else 0
        elif self._direction == 270:
            delta[0] = axes.X.value * d[0] if not x_zero else 0
            delta[1] = axes.Y.value * d[1] if not y_zero else 0
            delta[3] = -axes.RY.value * d[3] if not dx_zero else 0
            delta[4] = axes.RX.value * d[4] if not dy_zero else 0
        else:
            delta[0] = axes.Y.value * d[0] if not x_zero else 0
            delta[1] = -axes.X.value * d[1] if not y_zero else 0
            delta[3] = axes.RX.value * d[3] if not dx_zero else 0
            delta[4] = axes.RY.value * d[4] if not dy_zero else 0
        delta[2] = axes.Z.value * d[2]
        delta[5] = axes.RZ.value * d[5]

        return TeleopData(
            timestamp=time.monotonic(),
            space=TeleopSpace.CARTESIAN_DELTA,
            delta=delta,
            axes={
                'X': axes.X.value,
                'Y': axes.Y.value,
                'Z': axes.Z.value,
                'RX': axes.RX.value,
                'RY': axes.RY.value,
                'RZ': axes.RZ.value,
            },
            buttons={
                'START': int(buttons.START.value),
                'SELECT': int(buttons.SELECT.value),
                'A': int(buttons.A.value),
                'B': int(buttons.B.value),
                'X': int(buttons.X.value),
                'Y': int(buttons.Y.value),
                'DPAD_X': int(xbox.direction.X.value),
                'DPAD_Y': int(xbox.direction.Y.value),
            },
        )
