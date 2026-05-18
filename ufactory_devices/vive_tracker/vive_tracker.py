import sys
import ctypes
import logging
import threading
import pysurvive
import numpy as np
from ..transformations import Transformations

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('uf.vive_tracker')


class Vector(ctypes.Structure):
    def __getitem__(self, index):
        # 获取字段名列表
        field_name = self._fields_[index][0]
        # 使用 getattr 获取对应属性的值
        return getattr(self, field_name)

    def __setitem__(self, index, value):
        # 获取字段名列表
        field_name = self._fields_[index][0]
        # 使用 setattr 设置对应属性的值
        setattr(self, field_name, value)
    
    def __str__(self):
        return f'{self.to_list(6)}'
    
    def to_list(self, ndigits=6):
        return [round(getattr(self, item[0]), ndigits=ndigits) for item in self._fields_]


class Vector3D(Vector):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double)
    ]


class Vector4D(Vector):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
        ("w", ctypes.c_double)
    ]


class PoseData(ctypes.Structure):
    _fields_ = [
        ("position", Vector3D),
        # ("orientation", Vector3D),
        ("quaternion", Vector4D),
        ("hostTimestamp", ctypes.c_double),
        # ("edgeTimestampUs", ctypes.c_longlong),
        # ("confidence", ctypes.c_double)
    ]


class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ViveTracker(metaclass=SingletonMeta):
    # _instance = None
    # _initialized = False
    def __init__(self, config_path=None, lh_config=None, args=None):
        # if self._initialized:
        #     return
        # self._initialized = True
        self.config_path = config_path
        self.lh_config = lh_config
        self.args = args if args else []
        self.running = False
        self.context = None
        self.collector_thread = None
        self.data_lock = threading.Lock()
        self.latest_poses = {}
        self.latest_raw_poses = {}
        self.init()
    
    # def __new__(cls, *args, **kwargs):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #     return cls._instance
    
    def __del__(self):
        logger.info("正在停止Vive Tracker位姿追踪...")
        self.running = False
        # 等待线程结束
        if self.collector_thread:
            self.collector_thread.join(timeout=2.0)
        # 清理资源
        self.context = None
        logger.info("Vive Tracker已断开连接")
    
    @staticmethod
    def to_str(v):
        return v.decode("utf-8") if isinstance(v, bytes) else str(v)
    
    def list_devices(self):
        # import pysurvive
        # for obj in self.context.Objects():
        #     name = self.to_str(obj.Name())
        #     serial_number = None
        #     if hasattr(pysurvive, "simple_serial_number"):
        #         serial_number = self.to_str(pysurvive.simple_serial_number(obj.ptr))
        #     print("object:", name, "serial:", serial_number)
        return [key for key in self.latest_poses.keys() if not key.startswith('WM')]
    
    def init(self):
        # 构建pysurvive参数
        survive_args = sys.argv[:1]  # 保留程序名
        
        # 添加配置文件参数
        if self.config_path:
            survive_args.extend(['--config', self.config_path])
        
        # 添加灯塔配置参数
        if self.lh_config:
            survive_args.extend(['--lh', self.lh_config])
        
        # 添加其他参数
        survive_args.extend(self.args)
        try:
            logger.info("正在初始化pysurvive...")
            self.context = pysurvive.SimpleContext(survive_args)
            if not self.context:
                logger.error("错误: 无法初始化pysurvive上下文")
                return False

            logger.info("pysurvive初始化成功")
            # 标记为运行状态
            self.running = True

            # 创建并启动位姿收集线程
            self.collector_thread = threading.Thread(target=self._pose_collector)
            self.collector_thread.daemon = True
            self.collector_thread.start()
        except Exception as e:
            logger.error(f"连接Vive Tracker时发生错误: {e}")
            self.running = False
            return False
    
    def _pose_collector(self):
        initial_rotation = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, -30 / 180.0 * np.pi, 0, 0)

        # alignment_rotation = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, -np.pi / 2, -np.pi / 2, 0)
        alignment_rotation = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, -np.pi / 2, np.pi, np.pi)

        rotate_matrix = np.dot(initial_rotation, alignment_rotation)
        # 应用平移变换 - 将采集到的pose数据变换到夹爪中心
        # transform_matrix = Transformations.xyzrpy_to_rotation_matrix(0.172, 0, -0.076, 0, 0, 0)
        # transform_matrix = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, 0, 0, 0)

        # tracker_to_robot_matrix = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, np.pi, 0, np.pi)
        tracker_to_robot_matrix = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, 0, 0, -np.pi / 2)
        
        robot_base_matrix = Transformations.xyzrpy_to_rotation_matrix(*[0, 0, 0, np.pi, -np.pi / 2, 0])
        begin_tracker_robot_matrix = None
        
        cnt = 0
        
        # 持续获取最新位姿
        while self.running and self.context.Running():
            updated = self.context.NextUpdated()
            if not updated:
                continue
            if cnt < 100:
                cnt += 1
                continue
            # 获取设备名称
            device_name = str(updated.Name(), 'utf-8')
            serial_number = None
            if hasattr(pysurvive, "simple_serial_number"):
                serial_number = self.to_str(pysurvive.simple_serial_number(updated.ptr))
            # 获取位姿数据
            pose_obj = updated.Pose()
            pose_data = pose_obj[0]  # 位姿数据
            timestamp = pose_obj[1]  # 时间戳
            position = [pose_data.Pos[0], pose_data.Pos[1], pose_data.Pos[2]]
            quaternion = [pose_data.Rot[1], pose_data.Rot[2], pose_data.Rot[3], pose_data.Rot[0]]
            origin_mat = Transformations.xyzq_to_rotation_matrix(*position, quaternion)
            # tracker_matrix = np.dot(origin_mat, rotate_matrix)
            tracker_matrix = np.matmul(origin_mat, rotate_matrix)
            # tracker_matrix = np.matmul(np.matmul(origin_mat, rotate_matrix), transform_matrix)

            x, y, z, q = Transformations.rotation_matrix_to_xyzq(tracker_matrix)
            pose_data = PoseData(position=Vector3D(x, y, z), quaternion=Vector4D(*q), hostTimestamp=timestamp)
            pose_raw_data = PoseData(position=Vector3D(*position), quaternion=Vector4D(*quaternion), hostTimestamp=timestamp)
            with self.data_lock:
                self.latest_poses[device_name] = pose_data
                self.latest_raw_poses[device_name] = pose_raw_data
                if serial_number:
                    self.latest_poses[serial_number] = pose_data
                    self.latest_raw_poses[serial_number] = pose_raw_data

            # tracker_robot_matrix = np.dot(tracker_matrix, tracker_to_robot_matrix)
            # if begin_tracker_robot_matrix is None:
            #     begin_tracker_robot_matrix = tracker_robot_matrix
            # pose = Transformations.tracker_robot_matrix_to_robot_pose(begin_tracker_robot_matrix, tracker_robot_matrix, robot_base_matrix, is_axis_angle=True)

            # pose_data = PoseData(position=Vector3D(*pose[:3]), orientation=Vector3D(*pose[3:]), quaternion=Vector4D(*quaternion), hostTimestamp=timestamp)
            # with self.data_lock:
            #     self.latest_poses[device_name] = pose_data

    def get_pose(self, device_name=None):
        if device_name:
            with self.data_lock:
                if device_name in self.latest_poses:
                    return self.latest_poses[device_name]
                else:
                    return None
        else:
            with self.data_lock:
                return self.latest_poses.copy()
    
    def get_raw_pose(self, device_name=None):
        if device_name:
            with self.data_lock:
                if device_name in self.latest_raw_poses:
                    return self.latest_raw_poses[device_name]
                else:
                    return None
        else:
            with self.data_lock:
                return self.latest_raw_poses.copy()
