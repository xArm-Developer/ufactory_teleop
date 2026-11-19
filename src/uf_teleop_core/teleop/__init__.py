from .base import TeleopData, TeleopDevice, TeleopSpace
from .mapping import CartesianTeleopMapper

__all__ = [
    'TeleopData', 'TeleopDevice', 'TeleopSpace', 'CartesianTeleopMapper',
    'PikaTeleopDevice', 'UmiTeleopDevice', 'GelloTeleopDevice',
    'XboxTeleopDevice', 'SpacemouseTeleopDevice',
]


def __getattr__(name):
    # 延迟导入具体设备，避免加载未使用的 SDK 依赖
    if name == 'PikaTeleopDevice':
        from .pika_teleop_device import PikaTeleopDevice
        return PikaTeleopDevice
    if name == 'UmiTeleopDevice':
        from .umi_teleop_device import UmiTeleopDevice
        return UmiTeleopDevice
    if name == 'GelloTeleopDevice':
        from .gello_teleop_device import GelloTeleopDevice
        return GelloTeleopDevice
    if name == 'XboxTeleopDevice':
        from .xbox_teleop_device import XboxTeleopDevice
        return XboxTeleopDevice
    if name == 'SpacemouseTeleopDevice':
        from .spacemouse_teleop_device import SpacemouseTeleopDevice
        return SpacemouseTeleopDevice
    raise AttributeError('module {!r} has no attribute {!r}'.format(__name__, name))
