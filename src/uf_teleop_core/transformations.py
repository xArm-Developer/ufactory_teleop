import numpy as np


class Transformations:
    @staticmethod
    def quaternion_to_rotation_matrix(q):
        """
        将四元数转换为旋转矩阵
        
        注: 四元素顺序为xyzw
        """
        norm = np.linalg.norm(q)
        if norm < 1e-6:
            raise ValueError('零四元数无法归一化')

        x, y, z, w = q / norm  # 归一化
        xx, yy, zz = x * x, y * y, z * z
        xy, xz, yz = x * y, x * z, y * z
        wx, wy, wz = w * x, w * y, w * z

        R = np.array([
            [1 - 2 * (yy + zz),     2 * (xy - wz),      2 * (xz + wy)],
            [    2 * (xy + wz), 1 - 2 * (xx + zz),      2 * (yz - wx)],
            [    2 * (xz - wy),     2 * (yz + wx), 1 - 2 * (xx + yy)]
        ])
        return R

    @staticmethod
    def rotation_matrix_to_quaternion(R):
        """
        从 3x3 变换矩阵 或 4x4 齐次变换矩阵提取旋转部分并转换为四元数
        注: 四元素顺序为 xyzw
        """
        # 提取旋转矩阵部分
        rot_matrix = R[:3, :3]
        
        # 计算四元数
        trace = rot_matrix[0, 0] + rot_matrix[1, 1] + rot_matrix[2, 2]
        
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            qw = 0.25 / s
            qx = (rot_matrix[2, 1] - rot_matrix[1, 2]) * s
            qy = (rot_matrix[0, 2] - rot_matrix[2, 0]) * s
            qz = (rot_matrix[1, 0] - rot_matrix[0, 1]) * s
        elif rot_matrix[0, 0] > rot_matrix[1, 1] and rot_matrix[0, 0] > rot_matrix[2, 2]:
            s = 2.0 * np.sqrt(1.0 + rot_matrix[0, 0] - rot_matrix[1, 1] - rot_matrix[2, 2])
            qw = (rot_matrix[2, 1] - rot_matrix[1, 2]) / s
            qx = 0.25 * s
            qy = (rot_matrix[0, 1] + rot_matrix[1, 0]) / s
            qz = (rot_matrix[0, 2] + rot_matrix[2, 0]) / s
        elif rot_matrix[1, 1] > rot_matrix[2, 2]:
            s = 2.0 * np.sqrt(1.0 + rot_matrix[1, 1] - rot_matrix[0, 0] - rot_matrix[2, 2])
            qw = (rot_matrix[0, 2] - rot_matrix[2, 0]) / s
            qx = (rot_matrix[0, 1] + rot_matrix[1, 0]) / s
            qy = 0.25 * s
            qz = (rot_matrix[1, 2] + rot_matrix[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + rot_matrix[2, 2] - rot_matrix[0, 0] - rot_matrix[1, 1])
            qw = (rot_matrix[1, 0] - rot_matrix[0, 1]) / s
            qx = (rot_matrix[0, 2] + rot_matrix[2, 0]) / s
            qy = (rot_matrix[1, 2] + rot_matrix[2, 1]) / s
            qz = 0.25 * s
        
        return [qx, qy, qz, qw]

    @staticmethod
    def rpy_to_rotation_matrix(roll, pitch, yaw):
        """RPY角到旋转矩阵的转换"""
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)
        
        R = np.array([
            [cp*cy,  -cr*sy + sr*sp*cy,    sr*sy + cr*sp*cy],
            [cp*sy,   cr*cy + sr*sp*sy,   -sr*cy + cr*sp*sy],
            [ -sp,        sr*cp,               cr*cp],
        ])

        return R
    
    @staticmethod
    def rotation_matrix_to_rpy(R, yaw_zero=True):
        """
        旋转矩阵到RPY角的转换
        
        yaw_zero: 万向节锁情况下, True就把yaw置0, False就把roll置0
        返回: roll, pitch, yaw
        """
        epsilon = 1e-6
        if abs(R[2, 0]) > 1 - epsilon: # 万向节锁(pitch=±90°)
            pitch = np.arcsin(-R[2, 0])
            roll_yaw = np.arctan2(-R[0, 1], R[1, 1])
            if yaw_zero:
                # 保留roll, 把yaw置0
                roll, yaw = roll_yaw, 0
            else:
                # 保留yaw, 把roll置0
                roll, yaw = 0, roll_yaw
        else:
            roll = np.arctan2(R[2, 1], R[2, 2])
            pitch = np.arcsin(-R[2, 0])
            yaw = np.arctan2(R[1, 0], R[0, 0])

        return roll, pitch, yaw
    
    @staticmethod
    def rxryrz_to_rotation_matrix(rx, ry, rz):
        """轴角rxryrz到旋转矩阵的转换"""
        axis_angle = [rx, ry, rz]
        theta = np.linalg.norm(axis_angle)
        
        # 如果角度接近0，返回单位矩阵
        if theta < 1e-8:
            return np.eye(3)
        
        # 归一化旋转轴
        axis = axis_angle / theta
        x, y, z = axis
        
        c = np.cos(theta)
        s = np.sin(theta)
        t = 1 - c
        
        # 罗德里格斯旋转公式
        # R = I + sin(theta)*K + (1-cos(theta))*K^2
        # 展开为矩阵形式：
        R = np.array([
            [t*x*x + c,      t*x*y - s*z,  t*x*z + s*y],
            [t*x*y + s*z,    t*y*y + c,    t*y*z - s*x],
            [t*x*z - s*y,    t*y*z + s*x,  t*z*z + c]
        ])
        
        return R
    
    @staticmethod
    def rotation_matrix_to_rxryrz(R):
        """
        旋转矩阵到轴角的转换 (rx, ry, rz = axis * angle)
        返回: rx, ry, rz
        """
        R = np.asarray(R)
        if R.shape[-2:] != (3, 3):
            raise ValueError("Input must be (..., 3, 3)")
        
        # 计算旋转角度 theta
        trace = np.trace(R)
        cos_theta = (trace - 1) / 2.0
        cos_theta = np.clip(cos_theta, -1.0, 1.0)  # 防止数值误差导致 arccos 越界
        theta = np.arccos(cos_theta)
        eps = 1e-8

        # 情况 1: 无旋转 (theta ≈ 0)
        if theta < eps:
            axis = np.array([1.0, 0.0, 0.0])
            return axis * 0.0

        # 情况 2: 旋转角度接近 pi (180 度)
        if np.pi - theta < eps:
            # 此时 sin(theta) ≈ 0，不能用反对称公式
            # 从 R 对角线提取轴：R = I + 2 * (uu^T - I) => uu^T = (R + I)/2
            # 所以 u_i^2 = (R_ii + 1)/2
            diag = np.diag(R)
            axis = np.sqrt(np.maximum(diag + 1, 0))  # 取非负根
            
            # 确定符号：利用非对角元素，例如 R[0,1] = 2*u0*u1
            if axis[0] > eps:
                if R[0, 1] < 0:
                    axis[1] *= -1
                if R[0, 2] < 0:
                    axis[2] *= -1
            elif axis[1] > eps:
                if R[1, 2] < 0:
                    axis[2] *= -1
            # 注意：可能存在符号歧义，但旋转效果相同
            
            axis = axis / np.linalg.norm(axis)
            return axis * theta

        # 情况 3: 一般情况 (0 < theta < pi)
        sin_theta = np.sin(theta)
        axis = np.array([
            R[2, 1] - R[1, 2],
            R[0, 2] - R[2, 0],
            R[1, 0] - R[0, 1]
        ]) / (2 * sin_theta)

        axis = axis / np.linalg.norm(axis)  # 确保单位长度（数值误差可能破坏）
        return axis * theta
    
    @classmethod
    def xyzq_to_rotation_matrix(cls, x, y, z, q):
        T = np.eye(4)
        T[:3, :3] = cls.quaternion_to_rotation_matrix(q)
        T[:3, 3] = [x, y, z]
        return T

    @classmethod
    def xyzrpy_to_rotation_matrix(cls, x, y, z, roll, pitch, yaw):
        """构造4x4齐次变换矩阵"""
        T = np.eye(4)
        T[:3, :3] = cls.rpy_to_rotation_matrix(roll, pitch, yaw)
        T[:3, 3] = [x, y, z]
        return T
    
    @classmethod
    def xyzrxryrz_to_rotation_matrix(cls, x, y, z, rx, ry, rz):
        """构造4x4齐次变换矩阵"""
        T = np.eye(4)
        T[:3, :3] = cls.rxryrz_to_rotation_matrix(rx, ry, rz)
        T[:3, 3] = [x, y, z]
        return T

    @classmethod
    def rotation_matrix_to_xyzq(cls, rotation_matrix):
        """从4x4齐次变换矩阵到xyzq的转换"""
        x, y, z = rotation_matrix[0, 3], rotation_matrix[1, 3], rotation_matrix[2, 3]
        q = cls.rotation_matrix_to_quaternion(rotation_matrix[:3, :3])
        return [x, y, z, q]

    @classmethod
    def rotation_matrix_to_xyzrpy(cls, rotation_matrix):
        """从4x4齐次变换矩阵到xyzrpy的转换"""
        x, y, z = rotation_matrix[0, 3], rotation_matrix[1, 3], rotation_matrix[2, 3]
        roll, pitch, yaw = cls.rotation_matrix_to_rpy(rotation_matrix)
        return [x, y, z, roll, pitch, yaw]
    
    @classmethod
    def rotation_matrix_to_xyzrxryrz(cls, rotation_matrix):
        """从4x4齐次变换矩阵到xyzrxryrz的转换"""
        x, y, z = rotation_matrix[0, 3], rotation_matrix[1, 3], rotation_matrix[2, 3]
        rx, ry, rz = cls.rotation_matrix_to_rxryrz(rotation_matrix[:3,:3])
        return [x, y, z, rx, ry, rz]

    @classmethod
    def tracker_pose_to_robot_matrix(cls, x, y, z, q, tracker_to_robot_matrix):
        # Tracker位置对应的变换矩阵
        tracker_matrix = cls.xyzq_to_rotation_matrix(x, y, z, q)
        # Tracker位置转换到机械臂坐标系后对应的变换矩阵
        robot_matrix = np.dot(tracker_matrix, tracker_to_robot_matrix)
        return robot_matrix
    
    @classmethod
    def tracker_robot_matrix_to_robot_pose(cls, begin_tracker_robot_matrix, end_tracker_robot_matrix, robot_base_matrix, is_axis_angle=False):
        # 机械臂目标位置对应的变换矩阵
        # 机械臂目标 = 机械臂初始位置 + (当前手姿 - 初始手姿)
        delta_matrix = np.dot(np.linalg.inv(begin_tracker_robot_matrix), end_tracker_robot_matrix)
        robot_matrix = np.dot(robot_base_matrix, delta_matrix)
        if is_axis_angle:
            return cls.rotation_matrix_to_xyzrxryrz(robot_matrix)
        else:
            return cls.rotation_matrix_to_xyzrpy(robot_matrix)
