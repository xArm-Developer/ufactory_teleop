from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import numpy as np


class TeleopSpace(str, Enum):
    """遥操作数据结构类型。"""
    CARTESIAN = 'cartesian'              # 绝对位姿: position + quaternion
    CARTESIAN_DELTA = 'cartesian_delta'  # 增量位姿: delta
    JOINT = 'joint'                      # 关节角: joints


@dataclass
class TeleopData:
    """统一的遥操作数据帧。

    - position: [x, y, z]，单位米，设备坐标系
    - quaternion: 四元数 [x, y, z, w]（姿态）
    - joints: 关节角 (rad)
    - gripper: 0: 张开, 1: 闭合 (与 UFRobot 最后一位夹爪分量语义一致)
    - buttons: 按键/状态，如 pika 的 {"command": 0/1}
    - delta: [dx, dy, dz, drx, dry, drz]，单位 mm/rad，rpy 增量（手柄/SpaceMouse）
    - axes: 原始输入轴值，供零输入判断与数据采集（手柄/SpaceMouse）
    """
    timestamp: float
    space: TeleopSpace
    position: Optional[np.ndarray] = None
    quaternion: Optional[np.ndarray] = None
    joints: Optional[np.ndarray] = None
    gripper: Optional[float] = None
    buttons: Dict[str, int] = field(default_factory=dict)
    delta: Optional[np.ndarray] = None
    axes: Dict[str, float] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        if self.space == TeleopSpace.CARTESIAN:
            return self.position is not None and self.quaternion is not None
        if self.space == TeleopSpace.CARTESIAN_DELTA:
            return self.delta is not None
        return self.joints is not None


class TeleopDevice(ABC):
    """遥操作设备统一接口：只负责取数，不感知机器人。"""

    @abstractmethod
    def connect(self):
        """连接并初始化设备。"""

    @abstractmethod
    def close(self):
        """断开设备并释放资源。"""

    @abstractmethod
    def get_data(self) -> Optional[TeleopData]:
        """读取最新一帧数据。

        - 设备不可用 / 没有任何数据帧: 返回 None
        - 帧存在但关键数据缺失（如 tracker 丢失）: 返回 TeleopData，但 valid 为 False，
          buttons / gripper 等仍可用的字段照常填充
        """

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
