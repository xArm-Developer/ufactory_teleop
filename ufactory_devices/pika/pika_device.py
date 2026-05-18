import time
import logging
import threading
import serial
from serial.tools import list_ports

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pika_device')


def get_serial_ports(vidpid='1a86:7522'):
    """
    搜索所有指定vidpid的串口
    vidpid: 指定设备的VID:PID字符串, 默认值为'1a86:7522'
    返回找到的所有符合的串口号列表
    """
    ports = list_ports.comports()
    pika_ports = []
    for port in ports:
        if port.vid is not None and port.pid is not None:
            if '{:04x}:{:04x}'.format(port.vid, port.pid) == vidpid:
                pika_ports.append(port.device)
            # else:
            #     print('pidvid:', '{:04x}:{:04x}'.format(port.vid, port.pid))
    return pika_ports

def check_pika_device(port):
    """
    检测串口对应的Pika设备类型
    返回值:
        -1: 无法打开串口
        0: 不是Pika设备
        1: Pika Sense设备
        2: Pika Gripper设备
    """
    try:
        ser = serial.Serial(
            port=port,
            baudrate=460800,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        time.sleep(0.5)  # 等待串口稳定
        data = b''
        expired_time = time.monotonic() + 1.0  # 最多等待1秒
        while time.monotonic() < expired_time:
            if ser.in_waiting > 0:
                data += ser.read(ser.in_waiting)
                if len(data) > 200:  # 足够的数据来判断
                    break
            time.sleep(0.05)
        ser.close()
        data_str = data.decode('utf-8', errors='ignore')
        if '"Command"' in data_str or '"AS5047"' in data_str or '"IMU"' in data_str:
            # logger.info('✓ 检测到 Pika Sense 设备: {}'.format(port))
            return 1
        elif '"motor"' in data_str or '"motorstatus"' in data_str:
            # logger.info('✓ 检测到 Pika Gripper 设备: {}'.format(port))
            return 2
        else:
            # logger.info('✗ 未检测到 Pika 设备: {}, 数据长度: {}'.format(port, len(data)))
            return 0
    except:
        pass
    return -1


class PikaDevice(object):
    # _instance = None
    # _pika_sense_port = None
    # _pika_gripper_port = None
    # _lock = threading.Lock()

    def __init__(self, dev_type=1, **kwargs):
        """
        port: serial port
        dev_type: 1: sense, 2: gripper
        """
        if dev_type not in [1, 2, 3]:
            raise '不支持dev_type={}'.format(dev_type)
        
        self._dev_type = dev_type
        self._pika_sense_port = kwargs.get('pika_sense_port', None)
        self._pika_gripper_port = kwargs.get('pika_gripper_port', None)

        use_pika_sense = self._dev_type in [1, 3]
        use_pika_gripper = self._dev_type in [2, 3]

        if (use_pika_sense and self._pika_sense_port is None) or (use_pika_gripper and self._pika_gripper_port is None):
            pika_ports = get_serial_ports()
            if not pika_ports:
                logger.error('未找到Pika设备, 请检查连接')
                exit(1)

            for port in pika_ports:
                device_type = check_pika_device(port)
                if device_type == 1 and use_pika_sense and self._pika_sense_port is None:
                    self._pika_sense_port = port
                    logger.info('✓ 检测到 Pika Sense 设备: {}'.format(port))
                    if not use_pika_gripper:
                        break
                if device_type == 2 and use_pika_gripper and self._pika_gripper_port is None:
                    self._pika_gripper_port = port
                    logger.info('✓ 检测到 Pika Gripper 设备: {}'.format(port))
                    if not use_pika_sense:
                        break
        
            if use_pika_sense and self._pika_sense_port is None:
                logger.error('未找到Pika Sense设备, 请检查连接')
                exit(1)

            if use_pika_gripper and self._pika_gripper_port is None:
                logger.error('未找到Pika Gripper设备, 请检查连接')
                exit(1)

        if use_pika_sense:
            print('Pika Sense设备:', self._pika_sense_port)
        if use_pika_gripper:
            print('Pika Gripper 设备:', self._pika_gripper_port)

        self._pika_sense = None
        self._pika_gripper = None
        self.pika_tracker_device = None
    
    # def __new__(cls, *args, **kwargs):
    #     if not cls._instance:
    #         with cls._lock:
    #             if not cls._instance:
    #                 cls._instance = super().__new__(cls)
    #                 cls._instance.init(*args, *kwargs)
    #     return cls._instance
    
    def __del__(self):
        if self._pika_sense:
            self._pika_sense.disconnect()
        if self._pika_gripper:
            self._pika_gripper.disconnect()

    @property
    def pika_sense(self):
        if self._dev_type not in [1, 3]:
            return None
        if self._pika_sense is None:
            from pika.sense import Sense
            # 初始化Sense对象
            self._pika_sense = Sense(port=self._pika_sense_port)
            # 连接设备
            if not self._pika_sense.connect():
                logger.error('连接Pika Sense设备失败')
                exit(1)
            logger.info('Pika Sense设备连接成功')

            # 配置Vive Tracker（可选）
            # sense.set_vive_tracker_config(config_path='path/to/config', lh_config='lighthouse_config')

            tracker = self._pika_sense.get_vive_tracker()
            if not tracker:
                logger.error('Vive Tracker初始化失败')
                self._pika_sense.disconnect()
                exit(1)
            logger.info('Vive Tracker初始化成功')
            time.sleep(2)

            devices = self._pika_sense.get_tracker_devices()
            if not devices:
                logger.error('未检测到Vive Tracker设备')
                self._pika_sense.disconnect()
                exit(1)
            logger.info('检测到Vive Tracker设备: {}'.format(devices))

            self.pika_tracker_device = None
            for device in devices:
                if device.startswith('WM'):
                    self.pika_tracker_device = device
                    break
            else:
                self.pika_tracker_device = devices[0]
            logger.info('开始跟踪设备: {}\n'.format(self.pika_tracker_device))
        return self._pika_sense
    
    @property
    def pika_gripper(self):
        if self._dev_type not in [2, 3]:
            return None
        if self._pika_gripper is None:
            if self._dev_type in [2, 3]:
                from pika.gripper import Gripper
                self._pika_gripper = Gripper(port=self._pika_gripper_port)
                # 连接设备
                if not self._pika_gripper.connect():
                    logger.error('连接Pika Gripper设备失败')
                    if self._dev_type in [1, 3]:
                        self.pika_sense.disconnect()
                    exit(1)
                logger.info('Pika Gripper设备连接成功')
        return self._pika_gripper


if __name__ == '__main__':
    pika_device1 = PikaDevice(1)
    pika_device1.pika_sense
    pika_device1.pika_gripper
    time.sleep(3)

    # input('=================')

    pika_device2 = PikaDevice(2)
    pika_device2.pika_sense
    pika_device2.pika_gripper
    
    input('=================')

    print(pika_device1)
    print(pika_device1.pika_sense)
    print(pika_device1.pika_gripper)

    print(pika_device2)
    print(pika_device2.pika_sense)
    print(pika_device2.pika_gripper)

    input('=================')

    