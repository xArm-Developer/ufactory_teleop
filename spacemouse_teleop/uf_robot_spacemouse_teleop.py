#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import yaml
import logging
import argparse
import threading
from pathlib import Path
from typing import Tuple
from dataclasses import dataclass

from uf_teleop_core.teleop import SpacemouseTeleopDevice
from uf_teleop_core.robot import UFRobotConfig, UFRobot

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('spacemouse_teleop')

@dataclass
class SpaceMouseTeleopConfig:
    fps: int = 30
    leveling_speed: int = 45
    homing_speed: int = 45
    cartesian_speed: int = 200
    direction: int = 0  # 0: default, 90: rotate left, 180: rotate 180, 270: rotate right
    axes_deadzone: Tuple[int, ...] = (0.15, 0.15, 0.10, 0.15, 0.15, 0.10)
    max_distances: Tuple[int, ...] = (500, 500, 500, 60, 60, 60)


class UFRobotTeleop(object):
    def __init__(self, config: SpaceMouseTeleopConfig, robot_config: UFRobotConfig):
        self.config = config

        self.teleop = SpacemouseTeleopDevice(
            axes_deadzone=config.axes_deadzone,
            max_distances=config.max_distances,
            direction=config.direction,
        )
        self.teleop.connect()

        self.robot = UFRobot(robot_config)
        # 调平、回零、模式切换等底层操作仍通过机械臂 SDK 完成
        self.arm = self.robot.real_arm

        self._motion_type = 0
        self.cartesian_base_pose = [0, 0, 0, 0, 0, 0]
        self.cartesian_pose_delta = [0, 0, 0, 0, 0, 0]

        self._motion_thread = None

    def _robot_motion_loop(self):
        sleep_time = 1 / self.config.fps
        logger.info(f"[SpaceMouse] Robot motion loop started with {self.config.fps} FPS.")
        while self.arm and self.arm.connected:
            if self.arm.error_code != 0:
                time.sleep(1)
                continue

            if self._motion_type in [2, 3]:  # only positive: not yet executed
                if self.arm.mode != 0:
                    self.arm.set_mode(0)
                    self.arm.set_state(0)
                    time.sleep(0.2)
                elif self.arm.state in [4, 5]:
                    self.arm.set_state(0)
                    time.sleep(0.2)

                if self._motion_type == 2:  # leveling
                    logger.info(f"[SpaceMouse] Leveling started")
                    _, angles = self.arm.get_servo_angle()
                    if self.arm.axis == 5:
                        angles[3] = -(angles[1] + angles[2])
                    elif self.arm.axis == 6:
                        angles[3] = 0
                        angles[4] = -(angles[1] - angles[2]) if self.arm.arm.is_lite6 or self.arm.arm.is_850 else -(angles[1] + angles[2])
                    else:
                        _, pose = self.arm.get_position()
                        code, ret = self.arm.get_inverse_kinematics(pose=[*pose[:3], 180, 0, pose[5]])
                        if code == 0:
                            angles = ret
                    self.arm.set_servo_angle(angle=angles, speed=self.config.leveling_speed)
                else:  # zeroing
                    logger.info(f"[SpaceMouse] Homing started")
                    self.arm.move_gohome(speed=self.config.homing_speed)

                self._motion_type = -self._motion_type
                continue

            # ---- continuous cartesian motion ----
            if self._motion_type == 1:
                if self.arm.mode != 7:
                    self.arm.set_mode(7)
                    self.arm.set_state(0)
                    time.sleep(0.2)
                elif self.arm.state in [4, 5]:
                    self.arm.set_state(0)
                pose = [a + b for a, b in zip(
                    self.cartesian_base_pose, self.cartesian_pose_delta)]
                self.arm.set_position(*pose, speed=self.config.cartesian_speed)
            time.sleep(sleep_time)
        logger.info("[SpaceMouse] Robot motion loop completed.")

    def run(self):
        self._motion_thread = threading.Thread(target=self._robot_motion_loop, daemon=True)
        self._motion_thread.start()

        trigger_activated = False
        spacemouse_activated = False
        self._motion_type = 0

        left_cnt = 0
        right_cnt = 0
        left_button_long_pressed = False
        right_button_long_pressed = False
        zero = 0.01

        warning_logged = False

        logger.info("[SpaceMouse] Teleoperation started. Press LEFT + RIGHT for 0.5s to activate/deactivate control.")

        while self.arm and self.arm.connected:
            time.sleep(0.01)

            if not self.teleop.connected:
                if not warning_logged:
                    logger.warning("SpaceMouse controller is not connected. Please check the connection.")
                    warning_logged = True
                trigger_activated = False
                spacemouse_activated = False
                left_cnt = 0
                right_cnt = 0
                left_button_long_pressed = False
                right_button_long_pressed = False
                if self._motion_type != 0:
                    self._motion_type = 0
                    logger.info("[SpaceMouse] Motion over due to controller disconnection")
                    self.arm.set_state(6)
                continue
            warning_logged = False

            data = self.teleop.get_data()
            if data is None:
                continue
            axes = data.axes
            buttons = data.buttons

            btn_left_pressed = buttons['LEFT'] == 1
            btn_right_pressed = buttons['RIGHT'] == 1

            if btn_left_pressed: # left
                left_cnt += 1
                if left_cnt > 50 and not left_button_long_pressed:
                    left_button_long_pressed = True
            else:
                left_cnt = 0

            if btn_right_pressed: # right
                right_cnt += 1
                if right_cnt > 50 and not right_button_long_pressed:
                    right_button_long_pressed = True
            else:
                right_cnt = 0

            if left_button_long_pressed and right_button_long_pressed:
                # 双键长按0.5s切换激活/关闭
                if not trigger_activated:
                    spacemouse_activated = not spacemouse_activated
                    if spacemouse_activated:
                        logger.info("[SpaceMouse] Activated")
                    else:
                        logger.info("[SpaceMouse] Deactivated")
                trigger_activated = True

            is_trigger_zero_motion = spacemouse_activated and not trigger_activated and self.arm.connected

            if is_trigger_zero_motion and left_button_long_pressed and not btn_right_pressed:
                if abs(self._motion_type) not in [2, 3] and self.arm.error_code == 0:
                    self._motion_type = 2  # motion loop handles leveling
            elif is_trigger_zero_motion and right_button_long_pressed and not btn_left_pressed:
                if abs(self._motion_type) not in [2, 3] and self.arm.error_code == 0:
                    self._motion_type = 3  # motion loop handles zeroing

            # end leveling/zeroing on button release (pos=waiting, neg=executed)
            if abs(self._motion_type) == 2 and not btn_left_pressed:
                logger.info("[SpaceMouse] Leveling over")
                self._motion_type = 0
                self.arm.set_state(6)
            if abs(self._motion_type) == 3 and not btn_right_pressed:
                logger.info("[SpaceMouse] Homing over")
                self._motion_type = 0
                self.arm.set_state(6)

            if not spacemouse_activated:
                if not btn_left_pressed and not btn_right_pressed:
                    trigger_activated = False
                self._motion_type = 0
                left_button_long_pressed = False
                right_button_long_pressed = False
                continue

            if not btn_left_pressed:
                left_button_long_pressed = False
            if not btn_right_pressed:
                right_button_long_pressed = False
            if not btn_left_pressed and not btn_right_pressed:
                trigger_activated = False
            if abs(self._motion_type) in [2, 3] or trigger_activated:
                continue

            if self.arm.error_code != 0:
                if self._motion_type != 0:
                    self._motion_type = 0
                    logger.info("[SpaceMouse] Motion over due to robot error")
                    self.arm.set_state(6)
                    time.sleep(0.1)
                continue

            _xyz_is_zero = abs(axes['x']) <= zero and abs(axes['y']) <= zero and abs(axes['z']) <= zero
            _rpy_is_zero = abs(axes['roll']) <= zero and abs(axes['pitch']) <= zero and abs(axes['yaw']) <= zero

            if _xyz_is_zero and _rpy_is_zero:
                if self._motion_type != 0:
                    self._motion_type = 0
                    logger.info("[SpaceMouse] Motion over due to zero input")
                    self.arm.set_state(6)
                continue

            if self._motion_type == 0:
                self._motion_type = 1
                _, pose = self.arm.get_position()
                self.cartesian_base_pose = pose
                logger.info(f"[SpaceMouse] Cartesian motion started: {pose}")
            else:
                self.cartesian_pose_delta = list(data.delta)
        logger.info("[SpaceMouse] Teleoperation stopped.")


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
    teleop_confg = SpaceMouseTeleopConfig(**config['TeleoperatorConfig'])
    teleop = UFRobotTeleop(teleop_confg, robot_confg)

    time.sleep(1)

    print("\n********** Teleop Control Loop Start **********")
    teleop.run()
