from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np


class RobotActionSpace(str, Enum):
    """机器人动作空间类型。"""
    CARTESIAN = 'cartesian'  # [x, y, z, rx, ry, rz] (mm, rad)
    JOINT = 'joint'          # [j1, j2, ..., jn] (rad)


@dataclass
class RobotState:
    """机器人状态快照。"""
    tcp_pose: Optional[np.ndarray] = None    # [x, y, z, roll, pitch, yaw] (mm, rad)
    joints: Optional[np.ndarray] = None      # 关节角 (rad)
    gripper_norm: Optional[float] = None     # 0: 张开, 1: 闭合
    error_code: int = 0


class RobotDevice(ABC):
    """机器人设备统一接口。

    动作协议保持扁平数组：
    - CARTESIAN: [x, y, z, rx, ry, rz]，可选末尾追加 gripper_norm
    - JOINT:     [j1, ..., jn]，可选末尾追加 gripper_norm
    """

    @abstractmethod
    def connect(self):
        """连接并初始化机器人。"""

    @abstractmethod
    def close(self):
        """断开机器人连接并释放资源。"""

    @abstractmethod
    def get_state(self) -> RobotState:
        """读取当前机器人状态。"""

    @abstractmethod
    def send_action(self, action):
        """发送一帧动作，返回错误码 (0 表示成功)。"""

    @property
    @abstractmethod
    def action_space(self) -> RobotActionSpace:
        """当前动作空间类型。"""

    @property
    def connected(self) -> bool:
        return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
