import sys
import ctypes
import logging
import threading
import numpy as np
from .transformations import Transformations

logger = logging.getLogger('uf.vive_tracker')


class Vector(ctypes.Structure):
    def __getitem__(self, index):
        field_name = self._fields_[index][0]
        return getattr(self, field_name)

    def __setitem__(self, index, value):
        field_name = self._fields_[index][0]
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


class TrackerPose(ctypes.Structure):
    _fields_ = [
        ("position", Vector3D),
        ("quaternion", Vector4D),
        ("hostTimestamp", ctypes.c_double),
    ]


def _to_str(v):
    return v.decode("utf-8") if isinstance(v, bytes) else str(v)


class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ViveTracker(metaclass=SingletonMeta):
    def __init__(self, config_path=None, lh_config=None, args=None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._config_path = config_path
        self._lh_config = lh_config
        self._args = args if args else []
        self.running = False
        self._context = None
        self._collector_thread = None
        self._data_lock = threading.Lock()
        self._latest_poses = {}
        self._latest_raw_poses = {}
        if not self._init():
            raise RuntimeError("Failed to initialize Vive Tracker: pysurvive context creation failed")
    
    def __del__(self):
        logger.info("Stopping Vive Tracker pose tracking...")
        self.running = False
        # 等待线程结束
        if self._collector_thread:
            self._collector_thread.join(timeout=2.0)
        # 清理资源
        self._context = None
        logger.info("Vive Tracker disconnected")
    
    # def list_devices(self):
    #     import pysurvive
    #     for obj in self._context.Objects():
    #         name = _to_str(obj.Name())
    #         serial_number = None
    #         if hasattr(pysurvive, "simple_serial_number"):
    #             serial_number = _to_str(pysurvive.simple_serial_number(obj.ptr))
    #         print("object:", name, "serial:", serial_number)

    def get_tracked_device_names(self):
        return [key for key in self._latest_poses.keys() if not key.startswith('WM')]
    
    def _init(self):
        import pysurvive  # 延迟导入，避免未安装时影响 umi 包的整体导入
        self._pysurvive = pysurvive
        # 构建pysurvive参数
        survive_args = sys.argv[:1]  # 保留程序名
        
        # 添加配置文件参数
        if self._config_path:
            survive_args.extend(['--config', self._config_path])
        
        # 添加灯塔配置参数
        if self._lh_config:
            survive_args.extend(['--lh', self._lh_config])
        
        # 添加其他参数
        survive_args.extend(self._args)
        try:
            logger.info("Initializing pysurvive...")
            self._context = pysurvive.SimpleContext(survive_args)
            if not self._context:
                logger.error("Error: failed to initialize pysurvive context")
                return False

            logger.info("pysurvive initialized successfully")
            # 标记为运行状态
            self.running = True

            # 创建并启动位姿收集线程
            self._collector_thread = threading.Thread(target=self._pose_collector)
            self._collector_thread.daemon = True
            self._collector_thread.start()
        except Exception as e:
            logger.error(f"Error connecting to Vive Tracker: {e}")
            self.running = False
            return False
    
    def _pose_collector(self):
        if not hasattr(self, '_pysurvive'):
            return
        cnt = 0
        pysurvive = self._pysurvive

        # —————————————————————————————— 位姿变换矩阵常量 ——————————————————————————————
        # initial_rotation: 初始旋转补偿 (roll=-30°)
        _INITIAL_ROTATION = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, -30 / 180.0 * np.pi, 0, 0)
        # alignment_rotation: 坐标系对齐 (pitch=-90°, roll=180°, yaw=180°)
        # _ALIGNMENT_ROTATION = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, -np.pi / 2, -np.pi / 2, 0)
        _ALIGNMENT_ROTATION = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, -np.pi / 2, np.pi, np.pi)
        # rotate_matrix: 合并后的 tracker 坐标旋转矩阵
        _ROTATE_MATRIX = np.dot(_INITIAL_ROTATION, _ALIGNMENT_ROTATION)
        # 应用平移变换 - 将采集到的pose数据变换到夹爪中心
        # _TRANSFORM_MATRIX = Transformations.xyzrpy_to_rotation_matrix(0.172, 0, -0.076, 0, 0, 0)
        # _TRANSFORM_MATRIX = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, 0, 0, 0)
        # tracker_to_robot: tracker 到机械臂基座的固定变换
        _TRACKER_TO_ROBOT_MATRIX = Transformations.xyzrpy_to_rotation_matrix(0, 0, 0, 0, 0, -np.pi / 2)
        # robot_base: 机械臂基座位姿
        _ROBOT_BASE_MATRIX = Transformations.xyzrpy_to_rotation_matrix(*[0, 0, 0, np.pi, -np.pi / 2, 0])
        # 初始化阶段跳过帧数（让传感器数据稳定）
        _SKIP_FRAMES = 100
        # ———————————————————————————————————————————————————————————————————————————

        # 持续获取最新位姿
        while self.running and self._context.Running():
            updated = self._context.NextUpdated()
            if not updated:
                continue
            if cnt < _SKIP_FRAMES:
                cnt += 1
                continue
            # 获取设备名称，使用 replace 容错处理非 UTF-8 字节
            device_name = str(updated.Name(), 'utf-8', errors='replace')
            serial_number = None
            if hasattr(pysurvive, "simple_serial_number"):
                serial_number = _to_str(pysurvive.simple_serial_number(updated.ptr))
            # 获取位姿数据
            pose_obj = updated.Pose()
            pose_data = pose_obj[0]  # 位姿数据
            timestamp = pose_obj[1]  # 时间戳
            position = [pose_data.Pos[0], pose_data.Pos[1], pose_data.Pos[2]]
            quaternion = [pose_data.Rot[1], pose_data.Rot[2], pose_data.Rot[3], pose_data.Rot[0]]
            origin_mat = Transformations.xyzq_to_rotation_matrix(*position, quaternion)
            # tracker_matrix = np.dot(origin_mat, _ROTATE_MATRIX)
            tracker_matrix = np.matmul(origin_mat, _ROTATE_MATRIX)
            # tracker_matrix = np.matmul(np.matmul(origin_mat, _ROTATE_MATRIX), _TRANSFORM_MATRIX)

            x, y, z, q = Transformations.rotation_matrix_to_xyzq(tracker_matrix)
            tracker_pose = TrackerPose(position=Vector3D(x, y, z), quaternion=Vector4D(*q), hostTimestamp=timestamp)
            tracker_raw_pose = TrackerPose(position=Vector3D(*position), quaternion=Vector4D(*quaternion), hostTimestamp=timestamp)
            with self._data_lock:
                self._latest_poses[device_name] = tracker_pose
                self._latest_raw_poses[device_name] = tracker_raw_pose
                if serial_number:
                    self._latest_poses[serial_number] = tracker_pose
                    self._latest_raw_poses[serial_number] = tracker_raw_pose

    def get_pose(self, device_name=None):
        if device_name:
            with self._data_lock:
                if device_name in self._latest_poses:
                    return self._latest_poses[device_name]
                else:
                    return None
        else:
            with self._data_lock:
                return self._latest_poses.copy()
    
    def get_raw_pose(self, device_name=None):
        if device_name:
            with self._data_lock:
                if device_name in self._latest_raw_poses:
                    return self._latest_raw_poses[device_name]
                else:
                    return None
        else:
            with self._data_lock:
                return self._latest_raw_poses.copy()
