#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2026, Vinman, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.cub@gmail.com>

import os
import sys
import logging
import time
import timeit
import threading
from collections import namedtuple

# ---- backend selection ----
# Linux/macOS: always hidapi. Windows: SPACEMOUSE_BACKEND env var or auto-detect.
_HID_BACKEND = os.environ.get('SPACEMOUSE_BACKEND', '').lower()

if sys.platform != 'win32':
    # non-Windows: pywinusb is Windows-only, always use hidapi
    import hid as _hidapi
    _HID_BACKEND = 'hidapi'
elif _HID_BACKEND in ('hidapi', 'hid'):
    import hid as _hidapi
    _HID_BACKEND = 'hidapi'
elif _HID_BACKEND == 'pywinusb':
    from pywinusb import hid as _pywinusb
else:
    # Windows auto-detect: prefer pywinusb, fallback to hidapi
    try:
        from pywinusb import hid as _pywinusb
        _HID_BACKEND = 'pywinusb'
    except ImportError:
        try:
            import hid as _hidapi
            _HID_BACKEND = 'hidapi'
        except ImportError:
            raise ImportError('No HID backend available. Install pywinusb or hidapi, or set SPACEMOUSE_BACKEND.')

AxisSpec = namedtuple("AxisSpec", ["channel", "byte1", "byte2", "scale"])
ButtonSpec = namedtuple("ButtonSpec", ["channel", "byte", "bit"])

SpaceNavigator = namedtuple(
    "SpaceNavigator", ["t", "x", "y", "z", "roll", "pitch", "yaw", "buttons"]
)

SpaceDeviceSpec = namedtuple(
    'SpaceDeviceSpec',
    ['name', 'vendor_id', 'product_id', 'led_id', 'mappings', 'button_mapping', 'axis_scale']
)

space_device_map = {
    'SpaceNavigator': SpaceDeviceSpec(
        name='SpaceNavigator',
        vendor_id=0x46D,
        product_id=0xC626,
        led_id=[0x8, 0x4B],
        mappings={
            'x': AxisSpec(channel=1, byte1=1, byte2=2, scale=1),
            'y': AxisSpec(channel=1, byte1=3, byte2=4, scale=-1),
            'z': AxisSpec(channel=1, byte1=5, byte2=6, scale=-1),
            'pitch': AxisSpec(channel=2, byte1=1, byte2=2, scale=-1),
            'roll': AxisSpec(channel=2, byte1=3, byte2=4, scale=-1),
            'yaw': AxisSpec(channel=2, byte1=5, byte2=6, scale=1),
        },
        button_mapping=[
            ButtonSpec(channel=3, byte=1, bit=0),
            ButtonSpec(channel=3, byte=1, bit=1),
        ],
        axis_scale=350.0
    ),
    'SpaceMouse Compact': SpaceDeviceSpec(
        name='SpaceMouse Compact',
        vendor_id=0x256F,
        product_id=0xC635,
        led_id=[0x8, 0x4B],
        mappings={
            'x': AxisSpec(channel=1, byte1=1, byte2=2, scale=1),
            'y': AxisSpec(channel=1, byte1=3, byte2=4, scale=-1),
            'z': AxisSpec(channel=1, byte1=5, byte2=6, scale=-1),
            'pitch': AxisSpec(channel=2, byte1=1, byte2=2, scale=-1),
            'roll': AxisSpec(channel=2, byte1=3, byte2=4, scale=-1),
            'yaw': AxisSpec(channel=2, byte1=5, byte2=6, scale=1),
        },
        button_mapping=[
            ButtonSpec(channel=3, byte=1, bit=0),
            ButtonSpec(channel=3, byte=1, bit=1),
        ],
        axis_scale=350.0
    ),
    'SpaceMouse Wireless': SpaceDeviceSpec(
        name='SpaceMouse Wireless',
        vendor_id=0x256F,
        product_id=0xC62E,
        led_id=[0x8, 0x4B],
        mappings={
            'x': AxisSpec(channel=1, byte1=1, byte2=2, scale=1),
            'y': AxisSpec(channel=1, byte1=3, byte2=4, scale=-1),
            'z': AxisSpec(channel=1, byte1=5, byte2=6, scale=-1),
            'pitch': AxisSpec(channel=1, byte1=7, byte2=8, scale=-1),
            'roll': AxisSpec(channel=1, byte1=9, byte2=10, scale=-1),
            'yaw': AxisSpec(channel=1, byte1=11, byte2=12, scale=1),
        },
        button_mapping=[
            ButtonSpec(channel=3, byte=1, bit=0),
            ButtonSpec(channel=3, byte=1, bit=1),
        ],
        axis_scale=350.0
    ),
    # '3DConnexion Universal Receiver': SpaceDeviceSpec(
    #     name='3DConnexion Universal Receiver',
    #     vendor_id=0x256F,
    #     product_id=0xC652,
    #     led_id=[0x8, 0x4B],
    #     mappings={
    #         'x': AxisSpec(channel=1, byte1=1, byte2=2, scale=1),
    #         'y': AxisSpec(channel=1, byte1=3, byte2=4, scale=-1),
    #         'z': AxisSpec(channel=1, byte1=5, byte2=6, scale=-1),
    #         'pitch': AxisSpec(channel=1, byte1=7, byte2=8, scale=-1),
    #         'roll': AxisSpec(channel=1, byte1=9, byte2=10, scale=-1),
    #         'yaw': AxisSpec(channel=1, byte1=11, byte2=12, scale=1),
    #     },
    #     button_mapping=[
    #         ButtonSpec(channel=3, byte=1, bit=0),
    #         ButtonSpec(channel=3, byte=1, bit=1),
    #     ],
    #     axis_scale=350.0
    # ),
    'SpaceMouse Pro Wireless': SpaceDeviceSpec(
        name='SpaceMouse Pro Wireless',
        vendor_id=0x256F,
        product_id=0xC632,
        led_id=[0x8, 0x4B],
        mappings={
            'x': AxisSpec(channel=1, byte1=1, byte2=2, scale=1),
            'y': AxisSpec(channel=1, byte1=3, byte2=4, scale=-1),
            'z': AxisSpec(channel=1, byte1=5, byte2=6, scale=-1),
            'pitch': AxisSpec(channel=1, byte1=7, byte2=8, scale=-1),
            'roll': AxisSpec(channel=1, byte1=9, byte2=10, scale=-1),
            'yaw': AxisSpec(channel=1, byte1=11, byte2=12, scale=1),
        },
        button_mapping=[
            ButtonSpec(channel=3, byte=1, bit=0),  # MENU
            ButtonSpec(channel=3, byte=3, bit=7),  # ALT
            ButtonSpec(channel=3, byte=4, bit=1),  # CTRL
            ButtonSpec(channel=3, byte=4, bit=0),  # SHIFT
            ButtonSpec(channel=3, byte=3, bit=6),  # ESC
            ButtonSpec(channel=3, byte=2, bit=4),  # 1
            ButtonSpec(channel=3, byte=2, bit=5),  # 2
            ButtonSpec(channel=3, byte=2, bit=6),  # 3
            ButtonSpec(channel=3, byte=2, bit=7),  # 4
            ButtonSpec(channel=3, byte=2, bit=0),  # ROLL CLOCKWISE
            ButtonSpec(channel=3, byte=1, bit=2),  # TOP
            ButtonSpec(channel=3, byte=4, bit=2),  # ROTATION
            ButtonSpec(channel=3, byte=1, bit=5),  # FRONT
            ButtonSpec(channel=3, byte=1, bit=4),  # REAR
            ButtonSpec(channel=3, byte=1, bit=1),
        ],
        axis_scale=350.0
    ),
}


def to_int16(y1, y2):
    x = y1 | (y2 << 8)
    if x >= 32768:
        x = -(65536 - x)
    return x


def list_space_devices():
    """Enumerate connected SpaceMouse devices (cross-platform)."""
    devices = []
    if _HID_BACKEND == 'pywinusb':
        for device in _pywinusb.find_all_hid_devices():
            for name, spec in space_device_map.items():
                if device.vendor_id == spec.vendor_id and device.product_id == spec.product_id:
                    devices.append({'device': device, 'spec': spec})
    else:
        for dev_info in _hidapi.enumerate():
            vid = dev_info['vendor_id']
            pid = dev_info['product_id']
            for name, spec in space_device_map.items():
                if vid == spec.vendor_id and pid == spec.product_id:
                    devices.append({'info': dev_info, 'spec': spec})
    return devices


class ButtonState(list):
    def __int__(self):
        return sum((b << i) for (i, b) in enumerate(reversed(self)))


class SpaceDevice(threading.Thread):
    def __init__(self, axes_deadzone=[0.15, 0.15, 0.1, 0.15, 0.15, 0.1], logger=None):
        threading.Thread.__init__(self)
        self.daemon = True
        if not logger:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(logging.INFO)
            logger = logging.getLogger(__name__)
            logger.addHandler(stream_handler)
            logger.setLevel(logging.INFO)
        self.logger = logger
        self.device_name = ''
        self.device = None
        self.device_info = None
        self.spec = None
        self._connected = False
        self.state_changed_callbacks = []
        self.led_usage = None
        self._read_size = 64
        self.dict_state = {
            't': -1,
            'x': 0,
            'y': 0,
            'z': 0,
            'roll': 0,
            'pitch': 0,
            'yaw': 0,
            'buttons': [],
        }
        self.prev_state = None
        self.axes_deadzones = {
            'x': axes_deadzone[0],
            'y': axes_deadzone[1],
            'z': axes_deadzone[2],
            'roll': axes_deadzone[3],
            'pitch': axes_deadzone[4],
            'yaw': axes_deadzone[5],
        }
        self.tuple_state = SpaceNavigator(**self.dict_state)

    # ---- properties ----

    @property
    def connected(self):
        return self._connected

    @property
    def product_name(self):
        if _HID_BACKEND == 'pywinusb' and self.device:
            return self.device.product_name
        elif self.device_info:
            return self.device_info.get('product_string', '')
        return ''

    @property
    def vendor_name(self):
        if _HID_BACKEND == 'pywinusb' and self.device:
            return self.device.vendor_name
        elif self.device_info:
            return self.device_info.get('manufacturer_string', '')
        return ''

    @property
    def vendor_id(self):
        return self.spec.vendor_id if self.spec else 0

    @property
    def product_id(self):
        return self.spec.product_id if self.spec else 0

    @staticmethod
    def list_space_devices():
        return list_space_devices()
    
    def set_axes_deadzone(self, axes_deadzone):
        self.axes_deadzones['x'] = axes_deadzone[0]
        self.axes_deadzones['y'] = axes_deadzone[1]
        self.axes_deadzones['z'] = axes_deadzone[2]
        self.axes_deadzones['roll'] = axes_deadzone[3]
        self.axes_deadzones['pitch'] = axes_deadzone[4]
        self.axes_deadzones['yaw'] = axes_deadzone[5]

    # ---- lifecycle ----

    def run(self):
        """Main loop: keep device open, poll data (hidapi) or wait for callbacks (pywinusb)."""
        is_connected = False
        while True:
            if not is_connected:
                try:
                    self.open()
                    if self._connected:
                        is_connected = True
                    else:
                        time.sleep(1)
                        continue
                except Exception:
                    time.sleep(1)
                    continue

            if _HID_BACKEND == 'hidapi':
                # polling mode
                try:
                    data = self.device.read(self._read_size, timeout_ms=50)
                    if data:
                        self.process_data(data)
                except Exception as e:
                    self.logger.error('[SpaceMouse] disconnected, read error: {}'.format(e))
                    is_connected = False
                    self._connected = False
                    self.close()
                    time.sleep(1)
            else:
                # pywinusb: data comes via callback, just check connection
                try:
                    if not (self.device.is_plugged() and self.device.is_opened()):
                        self._connected = False
                        is_connected = False
                        self.logger.error('[SpaceMouse] disconnected')
                except Exception:
                    is_connected = False
                    self._connected = False
                time.sleep(0.5)

    def open(self):
        """Open the first matching SpaceMouse device."""
        self.close()
        devices = list_space_devices()
        if not devices:
            # self.logger.error('[SpaceMouse] device not found. Check: ls /dev/hidraw*')
            return

        if _HID_BACKEND == 'pywinusb':
            self._open_pywinusb(devices)
        else:
            self._open_hidapi(devices)

    def _open_pywinusb(self, devices):
        # prefer previously-used device
        item = devices[0]
        for dev in devices:
            d = dev['device']
            name = '{}-{}-{}'.format(d.vendor_name, d.product_name, d.instance_id)
            if name == self.device_name:
                item = dev
                break
        self.device = item['device']
        d = self.device
        self.device_name = '{}-{}-{}'.format(d.vendor_name, d.product_name, d.instance_id)
        self.spec = item['spec']

        self.device.open()
        self._connected = self.device.is_plugged() and self.device.is_opened()
        if not self._connected:
            return

        self.logger.info('[SpaceMouse] connected ({} backend)'.format(_HID_BACKEND))
        self.logger.info('[SpaceMouse] {}, {}, vendor_id:0x{:x}, product_id:0x{:x}, {}'.format(
            d.vendor_name, d.product_name, self.vendor_id, self.product_id, self.device_name))

        self.led_usage = _pywinusb.get_full_usage_id(self.spec.led_id[0], self.spec.led_id[1])
        self.dict_state = {
            't': -1, 'x': 0, 'y': 0, 'z': 0,
            'roll': 0, 'pitch': 0, 'yaw': 0,
            'buttons': ButtonState([0] * len(self.spec.button_mapping)),
        }
        self.tuple_state = SpaceNavigator(**self.dict_state)
        self.device.set_raw_data_handler(lambda data: self.process_data(data))

    def _open_hidapi(self, devices):
        # prefer previously-used by name
        item = devices[0]
        for dev in devices:
            info = dev['info']
            key = '{}-{}-{}'.format(
                info.get('manufacturer_string', ''),
                info.get('product_string', ''),
                info.get('serial_number', '')
            )
            if key == self.device_name:
                item = dev
                break

        info = item['info']
        self.spec = item['spec']
        self.device_info = info
        self.device_name = '{}-{}-{}'.format(
            info.get('manufacturer_string', ''),
            info.get('product_string', ''),
            info.get('serial_number', '')
        )
        while self.device_name.endswith('-'):
            self.device_name = self.device_name[:-1]

        # Try opening with both hidraw and libusb backends
        last_err = 'unknown'
        for backend in ('', 'libusb'):
            try:
                if backend:
                    os.environ['HIDAPI_DRIVER'] = backend
                self.device = _hidapi.device()
                self.device.open_path(info['path'])
                self.device.set_nonblocking(True)
                self._connected = True
                self.logger.info('[SpaceMouse] connected ({} backend)'.format(backend or 'hidraw'))
                self.logger.info('[SpaceMouse] {}, {}, vendor_id:0x{:x}, product_id:0x{:x}, {}'.format(
                    self.vendor_name, self.product_name, self.vendor_id, self.product_id, self.device_name))
                self.dict_state = {
                    't': -1, 'x': 0, 'y': 0, 'z': 0,
                    'roll': 0, 'pitch': 0, 'yaw': 0,
                    'buttons': ButtonState(
                        [0] * len(self.spec.button_mapping)),
                }
                self.tuple_state = SpaceNavigator(**self.dict_state)
                
                return
            except Exception as e:
                last_err = str(e)
                continue

        self._connected = False
        path = info.get('path', b'?')
        if isinstance(path, bytes):
            # libusb backend — needs USB device permissions
            self.logger.error('[SpaceMouse] failed to open ({}). Execute:\n'
                  '  echo \'SUBSYSTEM==\"usb\", ATTRS{{idVendor}}==\"256f\",'
                  ' MODE=\"0666\"\''
                  ' | sudo tee /etc/udev/rules.d/99-spacemouse.rules\n'
                  '  sudo udevadm control --reload && sudo udevadm trigger\n'
                  '  Then unplug and replug the device.\n'
                  '  Or switch to hidraw: sudo apt install libhidapi-hidraw0 &&'
                  ' pip install --force-reinstall hidapi'
                  .format(last_err))
        else:
            self.logger.error('[SpaceMouse] failed to open ({}) — ls -la {}'.format(
                last_err, path.decode() if isinstance(path, bytes) else path))

        self.dict_state = {
            't': -1, 'x': 0, 'y': 0, 'z': 0,
            'roll': 0, 'pitch': 0, 'yaw': 0,
            'buttons': ButtonState([0] * len(self.spec.button_mapping)),
        }
        self.tuple_state = SpaceNavigator(**self.dict_state)

    def close(self):
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
        self.device_info = None
        self._connected = False

    @property
    def state(self):
        return self.tuple_state

    # ---- LED ----

    def set_led(self, state):
        if not self.connected:
            return
        if _HID_BACKEND == 'pywinusb':
            self._set_led_pywinusb(state)
        else:
            self._set_led_hidapi(state)

    def _set_led_pywinusb(self, state):
        try:
            reports = self.device.find_output_reports()
            for report in reports:
                if self.led_usage in report:
                    report[self.led_usage] = state
                    report.send()
        except Exception:
            pass

    def _set_led_hidapi(self, state):
        try:
            self.device.send_feature_report([0x00, state])
        except Exception:
            try:
                self.device.write([0x00, state])
            except Exception:
                pass

    # ---- data processing ----

    def process_data(self, data):
        """Parse HID input report into axis/button state."""
        if self.prev_state is None:
            self.prev_state = {
                'x': 0, 'y': 0, 'z': 0, 'roll': 0, 'pitch': 0, 'yaw': 0,
                'buttons': ButtonState([0] * len(self.spec.button_mapping)),
            }
        for name, (chan, b1, b2, flip) in self.spec.mappings.items():
            if data[0] == chan:
                norm_val = flip * to_int16(data[b1], data[b2]) / float(self.spec.axis_scale)
                deadzone = self.axes_deadzones.get(name, None)
                if deadzone is not None:
                    dz = min(deadzone, 0.999)
                    if abs(norm_val) <= dz or deadzone >= 0.99:
                        norm_val = 0.0
                    else:
                        sign = 1 if norm_val >= 0 else -1
                        norm_val = sign * (abs(norm_val) - dz) / (1 - dz)
                norm_val = round(norm_val, 2)
                if norm_val > 0.1 and abs(norm_val - self.prev_state[name]) > 0.1:
                    self.dict_state[name] = norm_val
                    self.prev_state[name] = norm_val
                elif norm_val <= 0.1:
                    self.dict_state[name] = norm_val
                    self.prev_state[name] = norm_val
                # self.dict_state[name] = norm_val

        for btn_inx, (chan, byte, bit) in enumerate(self.spec.button_mapping):
            if data[0] == chan:
                mask = 1 << bit
                self.dict_state['buttons'][btn_inx] = 1 if (data[byte] & mask) != 0 else 0

        self.dict_state['t'] = timeit.default_timer()
        if len(self.dict_state) == 8:
            self.tuple_state = SpaceNavigator(**self.dict_state)

        for callback in self.state_changed_callbacks:
            callback(self.tuple_state)

    def register_state_changed_callback(self, callback):
        if callback not in self.state_changed_callbacks:
            self.state_changed_callbacks.append(callback)


if __name__ == '__main__':
    def state_changed_callback(state):
        print('x:{:.3f}, y:{:.3f}, z:{:.3f}, roll:{:.3f}, pitch:{:.3f}, yaw:{:.3f}, buttons:{}'.format(
            state.x, state.y, state.z, state.roll, state.pitch, state.yaw, state.buttons
        ))

    dev = SpaceDevice()
    dev.register_state_changed_callback(state_changed_callback)
    dev.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dev.close()
