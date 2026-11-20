#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
import argparse
import numpy as np
from typing import Tuple
from dataclasses import dataclass

from uf_teleop_core.config import load_config
from uf_teleop_core.teleop import UmiTeleopDevice, CartesianTeleopMapper
from uf_teleop_core.robot import UFRobotConfig, UFRobot

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('umi_teleop')

@dataclass
class UmiTeleopConfig:
    serial_number: str
    fps: int = 30
    use_gripper: bool = True
    use_vive_tracker: bool = False
    vive_tracker_id: str = 'WM0'
    tracker_to_robot_eef: Tuple[float, ...] = (0, 0, 0, 0, 0, -np.pi/2)
    robot_base_pose: Tuple[float, ...] = (300, 0, 300, np.pi, -np.pi/2, 0)


class UFRobotTeleop(object):
    def __init__(self, config: UmiTeleopConfig, robot_config: UFRobotConfig):
        self.config = config

        self.teleop = UmiTeleopDevice(
            serial_number=config.serial_number,
            use_gripper=config.use_gripper,
            use_vive_tracker=config.use_vive_tracker,
            vive_tracker_id=config.vive_tracker_id,
        )
        self.teleop.connect()

        # 遥操作位姿到机械臂目标位姿的映射
        self.mapper = CartesianTeleopMapper(
            config.tracker_to_robot_eef,
            robot_base_pose=config.robot_base_pose,
        )

        self.robot = UFRobot(robot_config)
        self.status = 2

    def set_status(self, status):
        self.status = status

    def run(self):
        sleep_time = 1 / self.config.fps

        while self.status > 0:
            time.sleep(sleep_time)

            if self.status != 1:
                continue

            data = self.teleop.get_data()
            if data is None or not data.valid:
                continue

            if not self.mapper.initialized:
                self.mapper.reset(data)

            robot_target_pose = self.mapper.map(data)
            if robot_target_pose is None:
                continue

            action = list(robot_target_pose)
            if self.config.use_gripper and data.gripper is not None:
                action.append(data.gripper)
            code = self.robot.send_action(action)
            if code != 0:
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='configuration args')
    parser.add_argument('-c', '--config', type=str, required=True,
                       help='configuration file path, e.g.my_config.yaml')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config yaml file: {e}")
        exit(1)

    robot_confg = UFRobotConfig(**config['RobotConfig'])
    teleop_confg = UmiTeleopConfig(**config['TeleoperatorConfig'])
    teleop = UFRobotTeleop(teleop_confg, robot_confg)

    time.sleep(1)

    print("\n********** Test Teleop With Robot **********")
    input('Enter to control robot with teleop >>> ')

    print("\n********** Teleop Control Loop Start **********")
    teleop.set_status(1)
    teleop.run()
