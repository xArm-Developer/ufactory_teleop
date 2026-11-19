import numpy as np


class GelloDevice(object):
    """Gello 主手驱动封装（Dynamixel + GelloAgent）。

    connect() 时读取当前关节角并计算零位偏移，然后创建 GelloAgent。
    gello 相关依赖在 connect() 内延迟导入。
    """

    def __init__(self, port=None, joint_ids=(1, 2, 3, 4, 5, 6, 7),
                 joint_signs=(1, 1, 1, 1, 1, 1, 1),
                 start_joints=(0, 0, 0, np.pi / 2, 0, np.pi / 2, 0),
                 gripper_id=8, torque_joint_ids=None, baudrate=57600):
        if not (len(joint_ids) == len(joint_signs) == len(start_joints)):
            raise ValueError('joint_ids, joint_signs and start_joints length mismatch')
        self._port = port
        self._joint_ids = joint_ids
        self._joint_signs = joint_signs
        self._start_joints = start_joints
        self._gripper_id = gripper_id
        self._torque_joint_ids = torque_joint_ids
        self._baudrate = baudrate

        self._action_dim = len(joint_ids) + (1 if gripper_id >= 0 else 0)
        self._fake_obs = dict({'joint_state': np.array([0.0] * self._action_dim)})
        self._gello_agent = None

    @property
    def connected(self) -> bool:
        return self._gello_agent is not None

    @property
    def action_dim(self) -> int:
        return self._action_dim

    @property
    def gripper_id(self) -> int:
        return self._gripper_id

    @property
    def gello_agent(self):
        return self._gello_agent

    def connect(self):
        if self._gello_agent is not None:
            return
        from gello.dynamixel.driver import DynamixelDriver
        from gello.agents.gello_agent import GelloAgent, DynamixelRobotConfig

        # 从当前 Gello 位姿自动计算关节零位偏移
        joint_ids = list(self._joint_ids)
        if self._gripper_id >= 0:
            joint_ids.append(self._gripper_id)
        driver = DynamixelDriver(joint_ids, port=self._port, baudrate=self._baudrate)
        for _ in range(10):
            driver.get_joints()  # warmup
        curr_joints = driver.get_joints()
        driver.close()

        joint_offsets = []
        for i in range(len(self._start_joints)):
            offset = curr_joints[i] - self._start_joints[i] / self._joint_signs[i]
            joint_offsets.append(offset)

        if self._gripper_id >= 0:
            gripper_config = [
                self._gripper_id,
                np.rad2deg(curr_joints[-1]) - 0.2,
                np.rad2deg(curr_joints[-1]) - 42,
            ]
        else:
            gripper_config = None

        param_dict = {
            'joint_ids': self._joint_ids,
            'joint_signs': self._joint_signs,
            'joint_offsets': joint_offsets,
            'gripper_config': gripper_config,
        }

        if self._torque_joint_ids:
            driver = DynamixelDriver(self._torque_joint_ids, port=self._port, baudrate=self._baudrate)
            driver.set_torque_mode(True)
            driver.close()

        dynamixel_config = DynamixelRobotConfig(**param_dict)
        print(dynamixel_config)
        self._gello_agent = GelloAgent(port=self._port, dynamixel_config=dynamixel_config)

    def get_action(self):
        """返回当前动作向量 [joints..., gripper]，未连接时返回 None。"""
        if self._gello_agent is None:
            return None
        action = np.asarray(self._gello_agent.act(self._fake_obs), dtype=float).reshape(-1)
        if len(action) != self._action_dim:
            raise ValueError('Joint action length must be {}, got {}'.format(self._action_dim, len(action)))
        return action

    def close(self):
        # GelloAgent 未提供显式关闭接口，释放引用即可
        self._gello_agent = None
