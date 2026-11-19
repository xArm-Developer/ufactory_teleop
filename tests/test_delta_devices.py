import numpy as np

from uf_teleop_core.teleop import SpacemouseTeleopDevice, XboxTeleopDevice

DISTANCES = (500, 500, 500, 60, 60, 60)


class _Axis:
    def __init__(self, value):
        self.value = value


class _Item:
    def __init__(self, value):
        self.value = value


class _Axes:
    def __init__(self, values):
        self.X, self.Y, self.Z, self.RX, self.RY, self.RZ = [_Axis(v) for v in values]


class _Buttons:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, _Item(value))


class _Direction:
    def __init__(self, x, y):
        self.X, self.Y = _Item(x), _Item(y)


class _FakeXbox:
    connected = True

    def __init__(self, values, buttons, dpad_x=0, dpad_y=0):
        self.axes = _Axes(values)
        self.buttons = _Buttons(**buttons)
        self.direction = _Direction(dpad_x, dpad_y)


def _xbox_expected(values, direction, x_zero=False, y_zero=False, dx_zero=False, dy_zero=False):
    x, y, z, rx, ry, rz = values
    d = DISTANCES
    out = [0.0] * 6
    if direction == 180:
        out[0] = -y * d[0] if not x_zero else 0
        out[1] = x * d[1] if not y_zero else 0
        out[3] = -rx * d[3] if not dx_zero else 0
        out[4] = -ry * d[4] if not dy_zero else 0
    elif direction == 90:
        out[0] = -x * d[0] if not x_zero else 0
        out[1] = -y * d[1] if not y_zero else 0
        out[3] = ry * d[3] if not dx_zero else 0
        out[4] = -rx * d[4] if not dy_zero else 0
    elif direction == 270:
        out[0] = x * d[0] if not x_zero else 0
        out[1] = y * d[1] if not y_zero else 0
        out[3] = -ry * d[3] if not dx_zero else 0
        out[4] = rx * d[4] if not dy_zero else 0
    else:
        out[0] = y * d[0] if not x_zero else 0
        out[1] = -x * d[1] if not y_zero else 0
        out[3] = rx * d[3] if not dx_zero else 0
        out[4] = ry * d[4] if not dy_zero else 0
    out[2] = z * d[2]
    out[5] = rz * d[5]
    return np.array(out)


def test_xbox_delta_matches_original_formula():
    values = (0.3, -0.4, 0.5, 0.2, -0.1, 0.6)
    buttons = dict(START=0, SELECT=0, A=0, B=0, X=0, Y=0)
    for direction in (0, 90, 180, 270):
        device = XboxTeleopDevice(direction=direction)
        device._xbox = _FakeXbox(values, buttons)
        data = device.get_data()
        np.testing.assert_allclose(data.delta, _xbox_expected(values, direction), atol=1e-12)
        assert data.valid


def test_xbox_delta_axis_lock_buttons():
    values = (0.3, -0.4, 0.5, 0.2, -0.1, 0.6)
    device = XboxTeleopDevice(direction=0)
    device._xbox = _FakeXbox(values, dict(START=0, SELECT=0, A=1, B=0, X=0, Y=0))
    data = device.get_data()
    expected = _xbox_expected(values, 0, x_zero=True, y_zero=True, dx_zero=False, dy_zero=True)
    np.testing.assert_allclose(data.delta, expected, atol=1e-12)


class _State:
    def __init__(self, values, buttons):
        self.x, self.y, self.z, self.roll, self.pitch, self.yaw = values
        self.buttons = buttons


class _FakeSpacemouse:
    connected = True

    def __init__(self, values, buttons):
        self.state = _State(values, buttons)


def _spacemouse_expected(values, direction):
    x, y, z, roll, pitch, yaw = values
    d = DISTANCES
    if direction == 180:
        return np.array([-y * d[0], x * d[1], z * d[2], -roll * d[3], -pitch * d[4], -yaw * d[5]])
    if direction == 90:
        return np.array([-x * d[0], -y * d[1], z * d[2], pitch * d[3], -roll * d[4], -yaw * d[5]])
    if direction == 270:
        return np.array([x * d[0], y * d[1], z * d[2], -pitch * d[3], roll * d[4], -yaw * d[5]])
    return np.array([y * d[0], -x * d[1], z * d[2], roll * d[3], pitch * d[4], -yaw * d[5]])


def test_spacemouse_delta_matches_original_formula():
    values = (0.2, -0.3, 0.4, 0.5, -0.6, 0.1)
    for direction in (0, 90, 180, 270):
        device = SpacemouseTeleopDevice(direction=direction)
        device._spacemouse = _FakeSpacemouse(values, [1, 0])
        data = device.get_data()
        np.testing.assert_allclose(data.delta, _spacemouse_expected(values, direction), atol=1e-12)
        assert data.buttons == {'LEFT': 1, 'RIGHT': 0}
        assert data.valid
