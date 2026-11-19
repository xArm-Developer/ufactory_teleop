#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import yaml
import logging
import argparse
import numpy as np
from pathlib import Path
from typing import Tuple
from dataclasses import dataclass

from uf_teleop_core.teleop import PikaTeleopDevice, CartesianTeleopMapper
from uf_teleop_core.robot import UFRobotConfig, UFRobot

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pika_teleop')

@dataclass
class PikaTeleopConfig:
    fps: int = 30
    use_gripper: bool = True
    pika_sense_port: str = None
    vive_tracker_id: str = None
    tracker_to_robot_eef: Tuple[float, ...] = (0, 0, 0, np.pi, -np.pi / 2, 0)


class UFRobotTeleop(object):
    def __init__(self, config: PikaTeleopConfig, robot_config: UFRobotConfig):
        self.config = config
        self.robot = UFRobot(robot_config)
        self.teleop = PikaTeleopDevice(
            pika_sense_port=config.pika_sense_port,
            vive_tracker_id=config.vive_tracker_id,
            use_gripper=config.use_gripper,
        )
        self.teleop.connect()
        self.mapper = CartesianTeleopMapper(config.tracker_to_robot_eef)
        self.status = 2

    def set_status(self, status):
        self.status = status

    def run(self):
        init_state = self.teleop.get_command_state()
        curr_state = init_state

        need_initial = False
        sleep_time = 1 / self.config.fps

        while self.status > 0:
            time.sleep(sleep_time)

            state = self.teleop.get_command_state()
            if state != curr_state:
                curr_state = state
                if self.status != 1 and curr_state != init_state:
                    self.status = 1
                    need_initial = True
                    self.robot.robot_init()
                    logger.info('开始遥操作')
                    time.sleep(1)
                elif self.status != 2 and curr_state == init_state:
                    self.status = 2
                    logger.info('停止遥操作')
                    continue

            if self.status != 1:
                continue

            data = self.teleop.get_data()
            if data is None or not data.valid:
                continue

            if need_initial:
                need_initial = False
                _, robot_pos = self.robot.get_position()
                logger.info('[初始] 机械臂位置: {}'.format(robot_pos))
                # 以当前遥操作位姿和机械臂位姿初始化映射
                self.mapper.reset(data, robot_pos)

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
        with open(Path(args.config).expanduser(), 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config yaml file: {e}")
        exit(1)

    robot_confg = UFRobotConfig(**config['RobotConfig'])
    teleop_confg = PikaTeleopConfig(**config['TeleoperatorConfig'])
    teleop = UFRobotTeleop(teleop_confg, robot_confg)

    time.sleep(1)

    print("\n********** Test Teleop With Robot **********")
    input('Enter to control robot with teleop >>> ')

    print("\n********** Teleop Control Loop Start **********")
    teleop.set_status(2)
    teleop.run()
