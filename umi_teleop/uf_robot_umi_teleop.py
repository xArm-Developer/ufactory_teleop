#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import yaml
import logging
import argparse
import numpy as np
from pathlib import Path
from typing import Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ufactory_devices.transformations import Transformations
from ufactory_devices.umi import XVLib
from ufactory_devices.robot import UFRobotConfig, UFRobot

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

        init_slam = not self.config.use_vive_tracker
        init_clamp_stream = self.config.use_gripper

        if self.config.use_vive_tracker:
            from ufactory_devices.vive_tracker import ViveTracker
            self.tracker = ViveTracker()
        else:
            self.tracker = None
        self.xvlib = XVLib(self.config.serial_number, init_slam, init_clamp_stream)

        self.robot = UFRobot(robot_config)

        tracker_to_robot_eef = self.config.tracker_to_robot_eef
        self.tracker_to_robot_matrix = Transformations.xyzrpy_to_rotation_matrix(*tracker_to_robot_eef)
        robot_base_pose = self.config.robot_base_pose
        self.robot_base_matrix = Transformations.xyzrpy_to_rotation_matrix(*robot_base_pose)
        self.begin_tracker_robot_matrix = None
        self.status = 2
    
    def set_status(self, status):
        self.status = status

    def run(self):
        sleep_time = 1 / self.config.fps
        gripper_norm = 0

        while self.status > 0:
            time.sleep(sleep_time)

            if self.status != 1:
                continue

            code = 0
            if self.tracker is not None:
                pose_data = self.tracker.get_pose(self.config.vive_tracker_id)
                if pose_data is None:
                    print('cant not get pose from vive tracker')
                    continue
            else:
                code, pose_data = self.xvlib.xv_get_slam_data()
            if code != 0:
                continue
            position = pose_data.position.to_list(6)
            quaternion = pose_data.quaternion.to_list(6)
            x, y, z = position[0] * 1000, position[1] * 1000, position[2] * 1000
            tracker_robot_matrix = Transformations.tracker_pose_to_robot_matrix(x, y, z, quaternion, self.tracker_to_robot_matrix)
            if self.begin_tracker_robot_matrix is None:
                self.begin_tracker_robot_matrix = tracker_robot_matrix

            robot_target_pose = Transformations.tracker_robot_matrix_to_robot_pose(self.begin_tracker_robot_matrix, tracker_robot_matrix, self.robot_base_matrix, is_axis_angle=True)
            x, y, z = robot_target_pose[0:3]
            orientation = robot_target_pose[3:6]

            action = [x, y, z, orientation[0], orientation[1], orientation[2]]

            if self.config.use_gripper:
                code, clamp_data = self.xvlib.xv_get_clamp_stream_data()
                if code == 0:
                    gripper_norm = (87 - clamp_data.data) / (87 - 0)
                action.append(gripper_norm)
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
    teleop_confg = UmiTeleopConfig(**config['TeleoperatorConfig'])
    teleop = UFRobotTeleop(teleop_confg, robot_confg)

    time.sleep(1)

    print("\n********** Test Teleop With Robot **********")
    input('Enter to control robot with teleop >>> ')

    print("\n********** Teleop Control Loop Start **********")
    teleop.set_status(1)
    teleop.run()
