#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2026, Vinman, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.cub@gmail.com>

import time
import sys
import logging
import threading
from dataclasses import dataclass

if sys.platform != 'win32':
    # Linux: prefer evdev over inputs (more reliable gamepad detection)
    try:
        import evdev
        _HAS_EVDEV = True
    except ImportError:
        _HAS_EVDEV = False
else:
    _HAS_EVDEV = False

from inputs import DeviceManager, UnpluggedError


def _find_xbox_evdev():
    """Find first Xbox-compatible gamepad via evdev (Linux)."""
    if not _HAS_EVDEV:
        return None
    try:
        devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
        for dev in devices:
            caps = dev.capabilities().get(evdev.ecodes.EV_ABS, [])
            abs_codes = {c[0] for c in caps}
            if evdev.ecodes.ABS_X in abs_codes and evdev.ecodes.ABS_Y in abs_codes:
                if evdev.ecodes.ABS_Z in abs_codes or evdev.ecodes.ABS_RX in abs_codes:
                    return dev
    except Exception:
        pass
    return None


@dataclass
class _JoyItem:
    name: str
    value: int
    timestamp: float


@dataclass
class _JoyAxis:
    name: str
    value: int
    timestamp: float
    max_val: int
    min_val: int
    deadzone: float


@dataclass
class _JoyAxes:
    X: _JoyAxis
    Y: _JoyAxis
    Z: _JoyAxis
    RX: _JoyAxis
    RY: _JoyAxis
    RZ: _JoyAxis


@dataclass
class _JoyButtons:
    START: _JoyItem
    SELECT: _JoyItem
    B: _JoyItem
    A: _JoyItem
    X: _JoyItem
    Y: _JoyItem


@dataclass
class _JoyDirection:
    X: _JoyItem
    Y: _JoyItem


class XBoxDevice(threading.Thread):
    def __init__(self, axes_deadzone=[0.15, 0.15, 0.1, 0.2, 0.2, 0.1], logger=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self._connected = False
        if not logger:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(logging.INFO)
            logger = logging.getLogger(__name__)
            logger.addHandler(stream_handler)
            logger.setLevel(logging.INFO)
        self.logger = logger
        self.axes = _JoyAxes(
            X=_JoyAxis('AXIS_X', 0, 0, 32767, -32768, axes_deadzone[0]),
            Y=_JoyAxis('AXIS_Y', 0, 0, 32767, -32768, axes_deadzone[1]),
            Z=_JoyAxis('AXIS_Z', 0, 0, 255, 0, axes_deadzone[2]),
            RX=_JoyAxis('AXIS_RX', 0, 0, 32767, -32768, axes_deadzone[3]),
            RY=_JoyAxis('AXIS_RY', 0, 0, 32767, -32768, axes_deadzone[4]),
            RZ=_JoyAxis('AXIS_RZ', 0, 0, 255, 0, axes_deadzone[5]),
        )
        self.buttons = _JoyButtons(
            START=_JoyItem('BTN_START', 0, 0),
            SELECT=_JoyItem('BTN_SELECT', 0, 0),
            B=_JoyItem('BTN_B', 0, 0),
            A=_JoyItem('BTN_A', 0, 0),
            X=_JoyItem('BTN_X', 0, 0),
            Y=_JoyItem('BTN_Y', 0, 0),
        )
        self.direction = _JoyDirection(
            X=_JoyItem('DIRCETION_X', 0, 0), # -1/0/1
            Y=_JoyItem('DIRCETION_Y', 0, 0), # -1/0/1
        )
        self.__joy_map = {
            'ABS_X': self.axes.X,
            'ABS_Y': self.axes.Y,
            'ABS_Z': self.axes.Z,
            'ABS_RX': self.axes.RX,
            'ABS_RY': self.axes.RY,
            'ABS_RZ': self.axes.RZ,
            'ABS_HAT0X': self.direction.X,
            'ABS_HAT0Y': self.direction.Y,
            'BTN_START': self.buttons.START,
            'BTN_SELECT': self.buttons.SELECT,
            'BTN_EAST': self.buttons.B,
            'BTN_SOUTH': self.buttons.A,
            'BTN_WEST': self.buttons.X,
            'BTN_NORTH': self.buttons.Y,
        }

    @property
    def connected(self):
        return self._connected
    
    def set_axes_deadzone(self, axes_deadzone):
        self.axes.X.deadzone = axes_deadzone[0]
        self.axes.Y.deadzone = axes_deadzone[1]
        self.axes.Z.deadzone = axes_deadzone[2]
        self.axes.RX.deadzone = axes_deadzone[3]
        self.axes.RY.deadzone = axes_deadzone[4]
        self.axes.RZ.deadzone = axes_deadzone[5]

    def _run_evdev(self, dev):
        """Read events from an evdev device (Linux)."""
        self.logger.info('[Xbox] connected (evdev) — {}'.format(dev.name))
        self._connected = True

        # ABS axes — try both standard and alternate codes
        abs_map = {}
        axis_targets = [
            (self.axes.X, (evdev.ecodes.ABS_X,), 32767, -32768, 1),
            (self.axes.Y, (evdev.ecodes.ABS_Y,), 32767, -32768, -1),
            (self.axes.Z, (evdev.ecodes.ABS_Z,), 1023, 0, 1),
            (self.axes.RX, (evdev.ecodes.ABS_RX,), 32767, -32768, 1),
            (self.axes.RY, (evdev.ecodes.ABS_RY,), 32767, -32768, -1),
            (self.axes.RZ, (evdev.ecodes.ABS_RZ,), 1023, 0, 1),
            (self.direction.X, (evdev.ecodes.ABS_HAT0X,), 0, 0, 1),
            (self.direction.Y, (evdev.ecodes.ABS_HAT0Y,), 0, 0, 1),
        ]
        for target, codes, max_val, min_val, scale in axis_targets:
            for code in codes:
                if code is not None:
                    abs_map[code] = (target, max_val, min_val, scale)

        # Buttons — try common aliases
        key_map = {}
        btn_targets = [
            (self.buttons.START, (evdev.ecodes.BTN_SELECT,)),
            (self.buttons.SELECT, (evdev.ecodes.BTN_START,)),
            (self.buttons.A, (evdev.ecodes.BTN_A,)),
            (self.buttons.B, (evdev.ecodes.BTN_B,)),
            (self.buttons.X, (evdev.ecodes.BTN_X,)),
            (self.buttons.Y, (evdev.ecodes.BTN_Y,)),
        ]
        for target, codes in btn_targets:
            for code in codes:
                key_map[code] = target

        try:
            for event in dev.read_loop():
                if event.type == evdev.ecodes.EV_ABS:
                    # ABS_X [左-32768, 右32767]
                    # ABS_Y [前-32768, 后32767]
                    # ABS_Z [松开0-1023按下]

                    # ABS_RX [左-32768, 右32767]
                    # ABS_RY [前-32768, 后32767]
                    # ABS_RZ [松开0-1023按下]
                    axis, max_val, min_val, scale = abs_map.get(event.code)
                    if axis:
                        val = event.value * scale
                        if isinstance(axis, _JoyAxis):
                            norm_val = val / (max_val if val >= 0 else abs(min_val))
                            dz = min(getattr(axis, 'deadzone', 0.0), 0.999)
                            if abs(norm_val) <= dz or dz >= 0.99:
                                norm_val = 0.0
                            else:
                                sign = 1 if norm_val >= 0 else -1
                                norm_val = sign * (abs(norm_val) - dz) / (1 - dz)
                            norm_val = round(norm_val, 2)
                        else:
                            norm_val = val
                        axis.value = norm_val
                        axis.timestamp = event.timestamp()
                elif event.type == evdev.ecodes.EV_KEY:
                    btn = key_map.get(event.code)
                    if btn:
                        btn.value = event.value
                        btn.timestamp = event.timestamp()
        except IOError:
            self.logger.error('[Xbox] disconnected (evdev)')
        finally:
            try:
                dev.close()
            except Exception:
                pass
            self._connected = False

    def run(self):
        is_connected = False
        device_manager = None

        while True:
            # -- detect / re-detect controller --
            if not is_connected:
                # Linux: prefer evdev (inputs has bugs with LED detection)
                if sys.platform != 'win32' and _HAS_EVDEV:
                    dev = _find_xbox_evdev()
                    if dev:
                        self._run_evdev(dev)
                        is_connected = False
                        self._connected = False
                        continue
                    time.sleep(1)
                    continue

                try:
                    device_manager = DeviceManager()
                    device_manager.codes['type_codes'] = {
                        v: k for k, v in device_manager.codes['types'].items()}
                except Exception:
                    time.sleep(1)
                    continue
                if not device_manager.gamepads:
                    if is_connected:
                        self.logger.error('[Xbox] disconnected')
                    is_connected = False
                    self._connected = False
                    time.sleep(1)
                    continue
                gamepad = device_manager.gamepads[0]
            if not is_connected:
                self.logger.info('[Xbox] connected')
            is_connected = True
            self._connected = True
            try:
                events = gamepad.read()
            except UnpluggedError:
                if is_connected:
                    self.logger.error('[Xbox] disconnected')
                self._connected = False
                is_connected = False
                time.sleep(1)
                continue
            except Exception as e:
                self.logger.error(f'[Xbox] read error: {e}')
                time.sleep(1)
                continue

            for event in events:
                ev_type = event.ev_type
                ev_code = event.code
                ev_state = event.state
                timestamp = event.timestamp
                if ev_type == 'Absolute':
                    # ABS_X [左-32768, 右32767]
                    # ABS_Y [前32767, 后-32768]
                    # ABS_Z [松开0-255按下]

                    # ABS_RX [左-32768, 右32767]
                    # ABS_RY [前32767, 后-32768]
                    # ABS_RZ [松开0-255按下]
                    if ev_code in ['ABS_X', 'ABS_Y', 'ABS_Z', 'ABS_RX', 'ABS_RY', 'ABS_RZ']:
                        axis = self.__joy_map[ev_code]
                        norm_val = ev_state / (axis.max_val if ev_state >= 0 else abs(axis.min_val))
                        dz = min(axis.deadzone, 0.999)
                        if abs(norm_val) <= dz or dz >= 0.99:
                            norm_val = 0.0
                        else:
                            sign = 1 if norm_val >= 0 else -1
                            norm_val = sign * (abs(norm_val) - dz) / (1 - dz)
                        norm_val = round(norm_val, 2)
                        axis.value = norm_val
                        axis.timestamp = timestamp
                        continue
                    elif ev_code in ['ABS_HAT0X', 'ABS_HAT0Y']:
                        direction = self.__joy_map[ev_code]
                        direction.value = ev_state
                        direction.timestamp = timestamp
                        continue
                    #     # self.logger.info('按下向左' if ev_state == -1 else '按下向右' if ev_state == 1 else '松开')
                    # elif ev_code == 'ABS_HAT0Y':
                    #     self.direction.Y.value = ev_state
                    #     self.direction.Y.timestamp = timestamp
                    #     # self.logger.info('按下向上' if ev_state == -1 else '按下向下' if ev_state == 1 else '松开')
                elif ev_type == 'Key':
                    if ev_code in ['BTN_START', 'BTN_SELECT', 'BTN_EAST', 'BTN_SOUTH', 'BTN_WEST', 'BTN_NORTH']:
                        button = self.__joy_map[ev_code]
                        button.value = ev_state
                        button.timestamp = timestamp
                        continue
                        # self.logger.info(f'按下{button.name}' if ev_state == 1 else '松开')

                # self.logger.info(f"类型: {event.ev_type}, 代码: {event.code}, 值: {event.state}, {event.device}, {event.timestamp}")
