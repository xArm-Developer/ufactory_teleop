from .base import RobotActionSpace, RobotDevice, RobotState

__all__ = [
    'RobotActionSpace', 'RobotDevice', 'RobotState',
    'UFRobotConfig', 'UFRobot',
]


def __getattr__(name):
    # 延迟导入，避免未安装 xarm SDK 时影响 base 接口的使用
    if name in ('UFRobotConfig', 'UFRobot'):
        from . import uf_robot
        return getattr(uf_robot, name)
    raise AttributeError('module {!r} has no attribute {!r}'.format(__name__, name))
