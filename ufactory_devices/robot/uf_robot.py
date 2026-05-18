import os
import sys
import time
import math
import struct
import logging
from dataclasses import dataclass
import numpy as np
from typing import Tuple
from enum import IntEnum
from xarm.wrapper import XArmAPI
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from ufactory_devices.pika import PikaDevice

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('uf.robot')


class GripperType(IntEnum):
    NoGripper = 0
    xArmGripper = 1
    xArmGripperG2 = 2
    BioGripperG2 = 3
    PikaGripper = 10
    RobotiqGripper = 11


@dataclass
class GripperParam:
    name: str
    open_pos: int
    close_pos: int
    speed: int = 0
    force: int = 0
    gripper_norm: float = 0

    def get_grippos(self, gripper_norm):
        pos = self.open_pos + gripper_norm * (self.close_pos - self.open_pos)
        min_pos, max_pos = min(self.open_pos, self.close_pos), max(self.open_pos, self.close_pos)
        return int(min(max(min_pos, pos), max_pos))
    
    def get_gripper_norm(self, grippos):
        if grippos is None:
            return self.gripper_norm
        self.gripper_norm = (self.open_pos - grippos) / (self.open_pos - self.close_pos)
        return self.gripper_norm


@dataclass
class UFRobotConfig:
    robot_ip: str = "192.168.1.127"
    robot_mode: int = 7         # 1: servo motion mode, 7: (default) cartesian online trajectory planning mode
    robot_speed: int = 250
    robot_acc: int = 1000
    gripper_type: int = 0       # 1: xArm Gripper, 2: xArm Gripper G2, 10: Pika Gripper, 11: Robotiq 2F-85
    gripper_port: str = None    # only used by pika gripper (gripper_type=10)
    gripper_speed: int = -1     # auto
    gripper_force: int = -1     # auto
    start_joints: Tuple[float, ...] = (0, 0, 0, np.pi/2, 0, np.pi/2, 0)
    start_tcp_pose: Tuple[float, ...] = None # xyzrpy


class UFRobot(object):
    def __init__(self, config: UFRobotConfig):
        self.config = config

        self._start_tcp_pose = self.config.start_tcp_pose
        self._start_joints = self.config.start_joints

        self._gripper_type = self.config.gripper_type
        if self._gripper_type == GripperType.xArmGripper:
            gripper_speed = 5000 if self.config.gripper_speed < 0 else min(max(50, self.config.gripper_speed), 5000)
            gripper_force = 50 if self.config.gripper_force < 0 else self.config.gripper_force # # not support
            self._gripper_param = GripperParam('xArmGripper', open_pos=800, close_pos=0, speed=gripper_speed, force=gripper_force)
        elif self._gripper_type == GripperType.xArmGripperG2:
            speed = 225 if self.config.gripper_speed < 0 else min(max(15, self.config.gripper_speed), 225)
            gripper_speed = int(((speed * 60) / 9.88235 + 140) / 0.4)
            gripper_force = 50 if self.config.gripper_force < 0 else min(max(1, self.config.gripper_force), 100)
            self._gripper_param = GripperParam('xArmGripperG2', open_pos=84, close_pos=0, speed=gripper_speed, force=gripper_force)
        elif self._gripper_type == GripperType.BioGripperG2:
            gripper_speed = 2000 if self.config.gripper_speed < 0 else min(max(500, self.config.gripper_speed), 4500)
            gripper_force = 100 if self.config.gripper_force < 0 else min(max(1, self.config.gripper_force), 100)
            self._gripper_param = GripperParam('BioGripperG2', open_pos=150, close_pos=71, speed=gripper_speed, force=gripper_force)
        elif self._gripper_type == GripperType.PikaGripper:
            self.pika_device = PikaDevice(2, pika_gripper_port=self.config.gripper_port)
            self.pika_gripper = self.pika_device.pika_gripper
            logger = logging.getLogger('pika.gripper')
            logger.setLevel(logging.WARNING)
            gripper_speed = 0 if self.config.gripper_speed < 0 else self.config.gripper_speed # not support
            gripper_force = 0 if self.config.gripper_force < 0 else self.config.gripper_force # not support
            self._gripper_param = GripperParam('PikaGripper', open_pos=100, close_pos=0, speed=gripper_speed, force=gripper_force)
        elif self._gripper_type == GripperType.RobotiqGripper:
            gripper_speed = 255 if self.config.gripper_speed < 0 else min(max(1, self.config.gripper_speed), 255)
            gripper_force = 255 if self.config.gripper_force < 0 else min(max(1, self.config.gripper_force), 255)
            self._gripper_param = GripperParam('RobotiqGripper', open_pos=0, close_pos=0xFF, speed=gripper_speed, force=gripper_force)
        else: # no gripper or not support
            self._gripper_type = 0
            self._gripper_param = GripperParam('NoGripper', open_pos=0, close_pos=0, speed=0, force=0)
        
        self.real_arm: XArmAPI
        self.connect()
    
    def connect(self):
        self.real_arm = XArmAPI(self.config.robot_ip)

        time.sleep(0.2)
        self._is_connected = self.real_arm.connected
        if not self._is_connected:
            print(f"UF Robot connection Failed, please check the hardware availability at ip: {self.config.robot_ip}")
            raise ConnectionError()

        if self._gripper_type == GripperType.PikaGripper:
            if not self.pika_gripper.connect():
                print('Could not connect to pika gripper.')
                raise ConnectionError()

        self.real_arm.motion_enable()
        self.real_arm.clean_error()
        self.real_arm.set_mode(0)  # set to idle mode
        self.real_arm.set_state(0)  # set to start state
        time.sleep(0.5)
        if self._start_tcp_pose is None:
            self.real_arm.set_servo_angle(angle=self._start_joints, is_radian=True, wait=True)
        else:
            self.real_arm.set_servo_angle(angle=self._start_joints, is_radian=True, wait=True)
            self.real_arm.set_position(*self._start_tcp_pose, speed=100, is_radian=True, wait=True)
            _, self._start_joints = self.real_arm.get_servo_angle(is_radian=True)
            self._start_tcp_pose = None

        self.real_arm.set_mode(self.config.robot_mode) 

        self.real_arm.set_state(0)

        _, err_warn = self.real_arm.get_err_warn_code()
        if err_warn[0] != 0:
            raise RuntimeError(f"Failed to set correct state to UF robot! Controller Error code: {err_warn[0]} !")

        if self._gripper_type > GripperType.NoGripper:
            self.real_arm._arm._baud_checkset = True
            if self._gripper_type == GripperType.xArmGripper:
                self.real_arm.set_gripper_enable(True)
                self.real_arm.set_gripper_mode(0)
                self.real_arm.set_gripper_speed(self._gripper_param.speed)
                self.real_arm.set_gripper_position(self._gripper_param.open_pos)
            elif self._gripper_type == GripperType.xArmGripperG2:
                self.real_arm.set_gripper_enable(True)
                self.real_arm.set_gripper_mode(0)
                self.real_arm.set_gripper_g2_position(self._gripper_param.open_pos)
            elif self._gripper_type == GripperType.BioGripperG2:
                _, mode = self.real_arm.get_bio_gripper_control_mode()
                if mode != 1:
                    self.real_arm.set_bio_gripper_control_mode(1)
                self.real_arm.set_bio_gripper_enable(True)
            elif self._gripper_type == GripperType.PikaGripper:
                self.pika_gripper.enable()
                time.sleep(0.5)
                self.pika_gripper.set_gripper_distance(self._gripper_param.open_pos)
            elif self._gripper_type == GripperType.RobotiqGripper:
                self.real_arm.robotiq_reset()
                self.real_arm.robotiq_set_activate(wait=True)
                self.real_arm.robotiq_set_position(self._gripper_param.open_pos, wait=True)
            self._gripper_param.grippos = self._gripper_param.open_pos
            self._gripper_param.gripper_norm = self._gripper_param.open_pos
            self.real_arm._arm._baud_checkset = False   
            _, err_warn = self.real_arm.get_err_warn_code()
            if err_warn[0] != 0:
                raise RuntimeError(f"Failed to set correct state to Gripper! Controller Error code: {err_warn[0]} !")
        self.real_arm.set_linear_spd_limit_factor(2.0)
        self.real_arm.set_collision_sensitivity(0)
    
    def get_position(self, is_axis_angle=False):
        if is_axis_angle:
            code, pos = self.real_arm.get_position_aa(is_radian=True)
        else:
            code, pos = self.real_arm.get_position(is_radian=True)
        return code, pos

    def send_action(self, action):
        if not self.real_arm.connected:
            raise ConnectionError()
        if self.real_arm.error_code != 0:
            return self.real_arm.error_code

        if self.config.robot_mode == 7:
            code = self.real_arm.set_position_aa(action[:6], is_radian=True, speed=self.config.robot_speed, mvacc=self.config.robot_acc, wait=False)
        else:
            code = self.real_arm.set_servo_cartesian_aa(action[:6], is_radian=True, speed=self.config.robot_speed, mvacc=self.config.robot_acc)
        
        if self._gripper_type > GripperType.NoGripper and len(action) > 6:
            gripper_norm = action[6]
            if self._gripper_type == GripperType.xArmGripper:
                grippos = self._gripper_param.get_grippos(gripper_norm)
                modbus_datas = [0x08, 0x10, 0x07, 0x00, 0x00, 0x02, 0x04]
                modbus_datas.extend(list(struct.pack('>i', grippos)))
                self.real_arm.getset_tgpio_modbus_data(modbus_datas)
                # self.real_arm.set_gripper_position(grippos, wait=False, wait_motion=False) # CHECK! the command unit
            elif self._gripper_type == GripperType.xArmGripperG2:
                grippos = self._gripper_param.get_grippos(gripper_norm)
                grippos = int((math.degrees(math.asin((grippos - 16) / 110)) + 8.33) * 18.28)
                modbus_datas = [0x08, 0x10, 0x0C, 0x00, 0x00, 0x05, 0x0A, 0x00, 0x01]
                modbus_datas.extend(list(struct.pack('>h', self._gripper_param.speed)))
                modbus_datas.extend(list(struct.pack('>h', self._gripper_param.force)))
                modbus_datas.extend(list(struct.pack('>i', grippos)))
                self.real_arm.getset_tgpio_modbus_data(modbus_datas)
            elif self._gripper_type == GripperType.BioGripperG2:
                grippos = self._gripper_param.get_grippos(gripper_norm)
                grippos = int(grippos * 3.7342 - 265.13)
                modbus_datas = [0x08, 0x10, 0x0C, 0x00, 0x00, 0x05, 0x0A, 0x00, 0x01]
                modbus_datas.extend(list(struct.pack('>h', self._gripper_param.speed)))
                modbus_datas.extend(list(struct.pack('>h', self._gripper_param.force)))
                modbus_datas.extend(list(struct.pack('>i', grippos)))
                self.real_arm.getset_tgpio_modbus_data(modbus_datas)
            elif self._gripper_type == GripperType.PikaGripper:
                grippos = self._gripper_param.get_grippos(gripper_norm)
                self.pika_gripper.set_gripper_distance(grippos)
            elif self._gripper_type == GripperType.RobotiqGripper:
                grippos = self._gripper_param.get_grippos(gripper_norm)
                modbus_datas = [0x09, 0x10, 0x03, 0xE8, 0x00, 0x03, 0x06, 0x09, 0x00, 0x00, grippos, self._gripper_param.speed, self._gripper_param.force]
                self.real_arm.getset_tgpio_modbus_data(modbus_datas)
                # self.real_arm.robotiq_set_position(
                #     grippos, speed=self._gripper_param.speed, force=self._gripper_param.force,
                #     wait=False, wait_motion=False,
                # )
        return code
