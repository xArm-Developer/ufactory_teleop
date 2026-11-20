#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
import argparse
import numpy as np
from typing import Tuple
from dataclasses import dataclass

from uf_teleop_core.config import load_config
from uf_teleop_core.teleop import GelloTeleopDevice
from uf_teleop_core.robot import UFRobotConfig, UFRobot

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('gello_teleop')

@dataclass
class GelloTeleopConfig:
    fps: int = 30
    port: str = None
    joint_ids: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
    joint_signs: Tuple[int, ...] = (1, 1, 1, 1, 1, 1, 1) # if follow the original open-sourced gello xarm7 setup
    start_joints: Tuple[float, ...] = (0, 0, 0, np.pi/2, 0, np.pi/2, 0)
    gripper_id: int = 8  # -1: no gripper
    torque_joint_ids: Tuple[int, ...] = None  # the joints will activate torque mode.


class UFRobotTeleop(object):
    def __init__(self, config: GelloTeleopConfig, robot_config: UFRobotConfig):
        self.config = config
        if robot_config.robot_mode != 6:
            raise ValueError("Gello teleop requires robot_mode=6 joint control mode")

        self.teleop = GelloTeleopDevice(
            port=config.port,
            joint_ids=config.joint_ids,
            joint_signs=config.joint_signs,
            start_joints=config.start_joints,
            gripper_id=config.gripper_id,
            torque_joint_ids=config.torque_joint_ids,
        )
        self.teleop.connect()

        self.robot = UFRobot(robot_config)
        self.status = 2

    def set_status(self, status):
        self.status = status

    def run(self):
        sleep_time = 1 / self.config.fps

        while self.status > 0:
            time.sleep(sleep_time)

            data = self.teleop.get_data()
            if data is None:
                continue

            action = list(data.joints)
            if data.gripper is not None:
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
    teleop_confg = GelloTeleopConfig(**config['TeleoperatorConfig'])
    teleop = UFRobotTeleop(teleop_confg, robot_confg)

    time.sleep(1)

    print("\n********** Test Teleop With Robot **********")
    input('Enter to control robot with teleop >>> ')

    print("\n********** Teleop Control Loop Start **********")
    teleop.set_status(1)
    teleop.run()
