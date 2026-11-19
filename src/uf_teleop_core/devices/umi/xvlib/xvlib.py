import os
import time
import threading
import ctypes
import ctypes.util
import logging
import numpy as np

logger = logging.getLogger('uf.xvlib')

# cv2 在 .frame() 方法中延迟导入，避免模块顶层强依赖 OpenCV
_cv2 = None
_rotate_codes = None


def _get_cv2():
    """延迟导入 cv2, 避免未安装 opencv 时阻塞模块加载"""
    global _cv2
    if _cv2 is None:
        import cv2 as _cv2_mod
        _cv2 = _cv2_mod
    return _cv2


def _get_rotate_codes():
    """延迟初始化旋转代码映射表"""
    global _rotate_codes
    if _rotate_codes is None:
        cv2 = _get_cv2()
        _rotate_codes = {
            90: cv2.ROTATE_90_CLOCKWISE,
            -90: cv2.ROTATE_90_COUNTERCLOCKWISE,
            180: cv2.ROTATE_180,
        }
    return _rotate_codes


def _apply_rotate(frame, rotate):
    """如果 rotate 不为 None, 对 frame 应用旋转"""
    if rotate is None or frame is None or (isinstance(rotate, int) and rotate == 0):
        return frame
    code = _get_rotate_codes().get(rotate) if isinstance(rotate, int) else rotate
    if code is None:
        logger.warning(f"Unknown rotate value: {rotate}, skipping")
        return frame
    return _get_cv2().rotate(frame, code)

# ============== 数据缓冲区常量 (与 C++ xv_device.h 保持一致) ==============
_MAX_COLOR_BUFFER_SIZE = 1280 * 1280 * 3    # MAX_COLOR_BUFFER_SIZE
_MAX_DEPTH_BUFFER_SIZE = 1280 * 1280 * 3    # MAX_DEPTH_BUFFER_SIZE
_MAX_GRAY_BUFFER_SIZE  = 640 * 480          # MAX_GRAY_BUFFER_SIZE
# =====================================================================


class DeviceStruct(ctypes.Structure):
    _fields_ = [
        ("serial_number", ctypes.c_char * 100)
    ]

    @property
    def serial(self):
        """返回解码后的序列号字符串"""
        return self.serial_number.decode('utf-8')

    def __repr__(self):
        return f"DeviceStruct(serial_number='{self.serial}')"


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


class Vector3B(Vector):
    _fields_ = [
        ("x", ctypes.c_bool),
        ("y", ctypes.c_bool),
        ("z", ctypes.c_bool)
    ]


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


class ClampData(ctypes.Structure):
    _pack_ = 1  # 匹配 SDK #pragma pack(1)
    _fields_ = [
        ("timestamp", ctypes.c_double),
        ("data", ctypes.c_double)
    ]


class ColorImageData(ctypes.Structure):
    _fields_ = [
        ("codec", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("data", ctypes.c_uint8 * _MAX_COLOR_BUFFER_SIZE),
        ("dataSize", ctypes.c_uint),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong)
    ]
    def frame(self, rgb=False, rotate=None):
        cv2 = _get_cv2()
        np_array = np.frombuffer(self.data, dtype=np.uint8, count=self.dataSize)
        if self.codec == 0: # YUYV 格式, 重塑为 (h, w, 2)，因为每两个字节包含 Y 和 UV 信息
            yuv_mat = np_array.reshape((self.height, self.width, 2))
            if rgb:
                frame = cv2.cvtColor(yuv_mat, cv2.COLOR_YUV2RGB_YUYV)
            else:
                frame = cv2.cvtColor(yuv_mat, cv2.COLOR_YUV2BGR_YUYV)
        elif self.codec == 1: # YU12 (即 I420) 格式 (UV 平面)
            yuv_mat = np_array.reshape((int(self.height * 1.5), self.width))
            if rgb:
                frame = cv2.cvtColor(yuv_mat, cv2.COLOR_YUV2RGB_I420)
            else:
                frame = cv2.cvtColor(yuv_mat, cv2.COLOR_YUV2BGR_I420)
        elif self.codec == 2: # JPEG 格式, 直接解码，不需要知道宽高（宽高包含在 JPEG 头中，但可以用 w,h 校验）
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        elif self.codec == 3: # NV12 格式 (UV 交错)
            yuv_mat = np_array.reshape((int(self.height * 1.5), self.width))
            if rgb:
                frame = cv2.cvtColor(yuv_mat, cv2.COLOR_YUV2RGB_NV12)
            else:
                frame = cv2.cvtColor(yuv_mat, cv2.COLOR_YUV2BGR_NV12)
        elif self.codec == 4: # BITSTREAM (H.264/H.265) 格式, 同样使用 imdecode，OpenCV 会自动处理常见的视频流头
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        else:
            frame = np_array
        return _apply_rotate(frame, rotate)


class DepthImageData(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("confidence", ctypes.c_double),
        ("data", ctypes.c_uint8 * _MAX_DEPTH_BUFFER_SIZE),
        ("dataSize", ctypes.c_uint),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong)
    ]
    def frame(self, rotate=None):
        cv2 = _get_cv2()
        np_array = np.frombuffer(self.data, dtype=np.uint8, count=self.dataSize)
        if self.type == 0: # Depth_16, 数据大小应为 w * h * 2
            # 1. 转换为 uint16 类型
            depth_uint16 = np_array.view(dtype=np.uint16).reshape((self.height, self.width))
            
            # 2. 归一化用于显示 (0-255)
            # 深度值通常在 0-65535 (mm)，直接显示是全黑的
            # cv2.normalize 将数据拉伸到 0-255 范围
            depth_norm = cv2.normalize(depth_uint16, None, 0, 255, cv2.NORM_MINMAX)
            depth_norm = np.uint8(depth_norm) # 转为 8位灰度图
            
            # 3. 可选：转为伪彩色以便观察
            depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
            frame = depth_color
        elif self.type == 1: # Depth_32, 数据大小应为 w * h * 4
            depth_float = np_array.view(dtype=np.float32).reshape((self.height, self.width))
        
            # 显示处理：截取有效范围 (例如 0-5米) 并归一化
            # 注意：这里假设最大值是 5000mm 或 5.0m，根据实际情况调整
            # max_depth = 5000.0 if np.max(depth_float) > 100 else 5.0
            depth_norm = cv2.normalize(depth_float, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
            frame = depth_color
        elif self.type == 2: # IR, 通常是 8位或16位灰度图, 数据大小可能是 w*h (8bit) 或 w*h*2 (16bit)
            # 尝试根据数据长度判断位深
            if len(np_array) == self.width * self.height:
                ir_img = np_array.reshape((self.height, self.width)) # 8位
            elif len(np_array) == self.width * self.height * 2:
                ir_img = np_array.view(dtype=np.uint16).reshape((self.height, self.width)) # 16位
                # 16位转8位显示
                ir_img = cv2.normalize(ir_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            else:
                logger.warning(f"IR data length mismatch: got {len(np_array)}, expected {self.width * self.height} or {self.width * self.height * 2}")
                return None
            # 转伪彩色
            ir_color = cv2.applyColorMap(ir_img, cv2.COLORMAP_JET)
            frame = ir_color
        elif self.type == 3: # Cloud, 这不是图像，是 xyz 坐标集合, 数据大小应为 w * h * 3 * 4 (float32) 或类似
            # 假设是 float32 格式
            cloud_data = np_array.view(dtype=np.float32).reshape((-1, 3))
            # cloud_data 现在是一个 N x 3 的数组，每一行是 (x, y, z)
            # 这里不返回图像，返回点云数据供 PCL 或 Open3D 处理
            frame = cloud_data
        elif self.type in [4, 5, 6]: # 4: Raw, 5: Eeprom, 6: IQ, 非图像数据，无法直接显示
            frame = None
        else:
            frame = np_array
        return _apply_rotate(frame, rotate)


class GrayScaleImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("data", ctypes.c_uint8 * _MAX_GRAY_BUFFER_SIZE)
    ]
    def frame(self, rotate=None):
        """返回 BGR 三通道图像，兼容 cv2.imshow 显示"""
        cv2 = _get_cv2()
        max_size = _MAX_GRAY_BUFFER_SIZE
        needed = self.width * self.height
        if needed > max_size:
            count = max_size
            h, w = 480, 640
        else:
            count = needed
            h, w = self.height, self.width
        gray = np.frombuffer(self.data, dtype=np.uint8, count=count).reshape((h, w))
        return _apply_rotate(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), rotate)


class FisheyeImagesData(ctypes.Structure):
    _fields_ = [
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("images", GrayScaleImage * 4),
        ("id", ctypes.c_longlong)
    ]

    # 四合一显示时的缩放尺寸 (宽度, 高度)
    _DISPLAY_WIDTH = 480
    _DISPLAY_HEIGHT = 360

    def frame(self, index=-1, rotate=None):
        index_valid = index >= 0 and index < 4
        if index_valid:
            return self.images[index].frame(rotate=rotate)
        else:
            cv2 = _get_cv2()
            frame0 = cv2.resize(self.images[0].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))
            frame1 = cv2.resize(self.images[1].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))
            frame2 = cv2.resize(self.images[2].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))
            frame3 = cv2.resize(self.images[3].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))

            up_frame = cv2.hconcat([frame0, frame1])
            down_frame = cv2.hconcat([frame2, frame3])
            return _apply_rotate(cv2.vconcat([up_frame, down_frame]), rotate)


class EyetrackingImageData(ctypes.Structure):
    _fields_ = [
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("images", GrayScaleImage * 4),
    ]

    # 四合一显示时的缩放尺寸 (宽度, 高度)
    _DISPLAY_WIDTH = 480
    _DISPLAY_HEIGHT = 360

    def frame(self, index=-1, rotate=None):
        index_valid = index >= 0 and index < 4
        if index_valid:
            return self.images[index].frame(rotate=rotate)
        else:
            cv2 = _get_cv2()
            frame0 = cv2.resize(self.images[0].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))
            frame1 = cv2.resize(self.images[1].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))
            frame2 = cv2.resize(self.images[2].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))
            frame3 = cv2.resize(self.images[3].frame(), (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT))

            up_frame = cv2.hconcat([frame0, frame1])
            down_frame = cv2.hconcat([frame2, frame3])
            return _apply_rotate(cv2.vconcat([up_frame, down_frame]), rotate)

# ============== 零拷贝 Ref 结构体 (直接引用 SDK 底层 buffer) ==============

class ColorImageDataRef(ctypes.Structure):
    _fields_ = [
        ("data_ptr", ctypes.c_void_p),
        ("data_size", ctypes.c_uint),
        ("codec", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
    ]
    def frame(self, rgb=False, rotate=None):
        """零拷贝帧解码 — 从 SDK buffer 指针直接构造 numpy 数组"""
        if self.data_size == 0 or not self.data_ptr:
            return None
        cv2 = _get_cv2()
        buf = (ctypes.c_uint8 * self.data_size).from_address(self.data_ptr)
        np_array = np.frombuffer(buf, dtype=np.uint8, count=self.data_size)
        if self.codec == 0:  # YUYV
            yuv_mat = np_array.reshape((self.height, self.width, 2))
            code = cv2.COLOR_YUV2RGB_YUYV if rgb else cv2.COLOR_YUV2BGR_YUYV
            frame = cv2.cvtColor(yuv_mat, code)
        elif self.codec == 1:  # I420
            yuv_mat = np_array.reshape((int(self.height * 1.5), self.width))
            code = cv2.COLOR_YUV2RGB_I420 if rgb else cv2.COLOR_YUV2BGR_I420
            frame = cv2.cvtColor(yuv_mat, code)
        elif self.codec in (2, 4):  # JPEG / BITSTREAM
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        elif self.codec == 3:  # NV12
            yuv_mat = np_array.reshape((int(self.height * 1.5), self.width))
            code = cv2.COLOR_YUV2RGB_NV12 if rgb else cv2.COLOR_YUV2BGR_NV12
            frame = cv2.cvtColor(yuv_mat, code)
        else:
            frame = np_array
        return _apply_rotate(frame, rotate)


class DepthImageDataRef(ctypes.Structure):
    _fields_ = [
        ("data_ptr", ctypes.c_void_p),
        ("data_size", ctypes.c_uint),
        ("type", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("confidence", ctypes.c_double),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
    ]
    def frame(self, rotate=None):
        """零拷贝深度帧解码"""
        if self.data_size == 0 or not self.data_ptr:
            return None
        cv2 = _get_cv2()
        buf = (ctypes.c_uint8 * self.data_size).from_address(self.data_ptr)
        np_array = np.frombuffer(buf, dtype=np.uint8, count=self.data_size)
        if self.type == 0:  # Depth_16
            depth_uint16 = np_array.view(dtype=np.uint16).reshape((self.height, self.width))
            depth_norm = cv2.normalize(depth_uint16, None, 0, 255, cv2.NORM_MINMAX)
            frame = cv2.applyColorMap(np.uint8(depth_norm), cv2.COLORMAP_JET)
        elif self.type == 1:  # Depth_32
            depth_float = np_array.view(dtype=np.float32).reshape((self.height, self.width))
            depth_norm = cv2.normalize(depth_float, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            frame = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
        elif self.type == 2:  # IR
            if len(np_array) == self.width * self.height:
                ir_img = np_array.reshape((self.height, self.width))
            elif len(np_array) == self.width * self.height * 2:
                ir_img = np_array.view(dtype=np.uint16).reshape((self.height, self.width))
                ir_img = cv2.normalize(ir_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            else:
                logger.warning(f"IR data length mismatch: got {len(np_array)}")
                return None
            frame = cv2.applyColorMap(ir_img, cv2.COLORMAP_JET)
        elif self.type == 3:  # Cloud
            frame = np_array.view(dtype=np.float32).reshape((-1, 3))
        elif self.type in (4, 5, 6):
            return None
        else:
            frame = np_array
        return _apply_rotate(frame, rotate)


class GrayScaleImageRef(ctypes.Structure):
    _fields_ = [
        ("data_ptr", ctypes.c_void_p),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
    ]
    def frame(self, rotate=None):
        if not self.data_ptr or self.width <= 0:
            return None
        cv2 = _get_cv2()
        buf = (ctypes.c_uint8 * (self.width * self.height)).from_address(self.data_ptr)
        gray = np.frombuffer(buf, dtype=np.uint8, count=self.width * self.height).reshape((self.height, self.width))
        return _apply_rotate(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), rotate)


class FisheyeImagesDataRef(ctypes.Structure):
    _fields_ = [
        ("images", GrayScaleImageRef * 4),
        ("image_count", ctypes.c_int),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("id", ctypes.c_longlong),
    ]
    _DISPLAY_WIDTH = 480
    _DISPLAY_HEIGHT = 360

    def frame(self, index=-1, rotate=None):
        if index >= 0 and index < self.image_count:
            return self.images[index].frame(rotate=rotate)
        return self._four_in_one(self.image_count, rotate)

    def _four_in_one(self, count, rotate=None):
        cv2 = _get_cv2()
        frames = []
        for i in range(count):
            f = self.images[i].frame()
            if f is not None:
                frames.append(cv2.resize(f, (self._DISPLAY_WIDTH, self._DISPLAY_HEIGHT)))
        if not frames:
            return None
        while len(frames) < 4:
            frames.append(frames[-1])
        up = cv2.hconcat([frames[0], frames[1]])
        down = cv2.hconcat([frames[2], frames[3]])
        return _apply_rotate(cv2.vconcat([up, down]), rotate)
    
class EyetrackingImageDataRef(ctypes.Structure):
    _fields_ = [
        ("images", GrayScaleImageRef * 4),
        ("image_count", ctypes.c_int),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
    ]

    def frame(self, index=-1, rotate=None):
        if index >= 0 and index < self.image_count:
            return self.images[index].frame(rotate=rotate)
        return None

# =====================================================================


class PoseData(ctypes.Structure):
    _fields_ = [
        ("position", Vector3D),
        # ("orientation", Vector3D),
        ("quaternion", Vector4D),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("confidence", ctypes.c_double)
    ]


class ImuData(ctypes.Structure):
    _pack_ = 1  # 匹配 SDK #pragma pack(1)
    _fields_ = [
        ("gyro", Vector3D),
        ("accel", Vector3D),
        ("accelSaturation", Vector3B),
        ("magneto", Vector3D),
        ("temperature", ctypes.c_double),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong)
    ]


class EventData(ctypes.Structure):
    _pack_ = 1  # 匹配 SDK #pragma pack(1)
    _fields_ = [
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("type", ctypes.c_int),
        ("state", ctypes.c_int)
    ]


class OrientationData(ctypes.Structure):
    """6-DOF 方向数据：四元数 + 3x3 旋转矩阵"""
    _fields_ = [
        ("quaternion", Vector4D),
        ("rotation", ctypes.c_double * 9),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
    ]


class XVLib:
    _xvlib = None
    _load_lock = threading.Lock()

    def __init__(self, serial_number, init_slam=False, init_clamp_stream=False, init_color_camera=False, init_fisheye_cameras=False):
        self.instance_id = -1

        self._clamp_data = ClampData()
        self._event_data = EventData()
        self._color_image_data = ColorImageData()
        self._depth_image_data = DepthImageData()
        self._fisheye_images_data = FisheyeImagesData()
        self._eyetracking_image_data = EyetrackingImageData()
        self._slam_data = PoseData()
        self._external_stream_data = PoseData()
        self._spheretrack_stream_data = PoseData()
        self._orientation_data = OrientationData()

        # 零拷贝 Ref 数据 holder
        self._color_image_data_ref = ColorImageDataRef()
        self._depth_image_data_ref = DepthImageDataRef()
        self._fisheye_images_data_ref = FisheyeImagesDataRef()
        self._eyetracking_image_data_ref = EyetrackingImageDataRef()

        self.__load_library()

        # 等待设备注册完成再初始化（自己有重试循环，不用 xv_get_devices 的 double_query）
        sn_bytes = serial_number.encode('utf-8')
        for i in range(3):
            _, devices = self.xv_get_devices(timeout=5.0 - i, double_query=False)
            sn_list = [d.serial for d in devices]
            if serial_number in sn_list:
                break
            time.sleep(1)
        else:
            raise Exception(f'Device {serial_number} not detected')

        c_serial_number = ctypes.c_char_p(sn_bytes)
        self.instance_id = self.xv_init(c_serial_number, init_slam, init_clamp_stream, init_color_camera, init_fisheye_cameras)
        if self.instance_id > 0:
            logger.info('Device initialized successfully.')
        else:
            raise Exception(f'Device initialized failure (ret={self.instance_id}).')
    
    def __del__(self):
        self.xv_uninit()
    
    _DEB_URL = ("https://raw.githubusercontent.com/xArm-Developer/"
                "ufactory_resources/main/fastumi/sdk/XVSDK_focal_amd64.deb")

    @classmethod
    def _check_xvsdk(cls):
        """检查系统是否安装了 XVSDK, 没有则抛异常并提示安装命令."""
        if ctypes.util.find_library("xvsdk"):
            candidate_paths = [
                '/usr/lib/libxvsdk.so',
                '/usr/lib/x86_64-linux-gnu/libxvsdk.so',
                '/usr/lib/aarch64-linux-gnu/libxvsdk.so',
                '/usr/local/lib/libxvsdk.so',
            ]
            if any(os.path.exists(p) for p in candidate_paths):
                return
        raise RuntimeError(
            "XVSDK not found. Run:\n"
            f"  curl -sL {cls._DEB_URL} -o /tmp/xvsdk.deb && sudo dpkg -i /tmp/xvsdk.deb\n"
            "  sudo apt install -y --fix-broken")

    @classmethod
    def _find_system_lib(cls, fname):
        """在系统标准路径中搜索精确版本 .so."""
        for base in ["/usr/lib", "/usr/lib/x86_64-linux-gnu", "/usr/local/lib"]:
            path = os.path.join(base, fname)
            if os.path.exists(path):
                return path
        # find_library 兜底，但必须版本匹配
        lib_name = fname.split(".so")[0]  # "libopencv_core"
        if lib_name.startswith("lib"):
            lib_name = lib_name[3:]  # "opencv_core"
        sys_lib = ctypes.util.find_library(lib_name)
        if sys_lib and fname in sys_lib:
            return sys_lib
        return None

    @classmethod
    def _load_tbb_lib(cls, lib_dir):
        """预加载 libtbb.so.2，解决 bundled OpenCV 的 TBB 依赖。

        策略: 系统路径(apt 安装) → 本地 bundled 版本。
        bundled libopencv_core.so.4.2 依赖旧版 libtbb.so.2 (Intel TBB 2.x ABI)，
        而 Ubuntu 22.04+ 的 oneAPI TBB (libtbb.so.12) 不兼容，必须显式预加载。
        """
        tbb_paths = [
            '/usr/lib/x86_64-linux-gnu/libtbb.so.2',
            '/usr/lib/libtbb.so.2',
            '/usr/local/lib/libtbb.so.2',
        ]
        for p in tbb_paths:
            if os.path.exists(p):
                try:
                    ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
                    logger.info(f'Loaded libtbb.so.2 from system ({p})')
                    return
                except OSError:
                    pass

        local_path = os.path.join(lib_dir, 'libtbb.so.2')
        if os.path.exists(local_path):
            ctypes.CDLL(local_path, mode=ctypes.RTLD_GLOBAL)
            logger.info('Loaded libtbb.so.2 from local (bundled)')
            return

        logger.warning('libtbb.so.2 not found, OpenCV loading may fail')

    @classmethod
    def _load_opencv_lib(cls, lib_dir, fname):
        """加载 opencv .so: 系统(精确版本) → 本地目录."""
        sys_path = cls._find_system_lib(fname)
        if sys_path:
            try:
                ctypes.CDLL(sys_path, mode=ctypes.RTLD_GLOBAL)
                logger.info(f"Loaded {fname} from system ({sys_path})")
                return
            except OSError:
                logger.debug(f"System {fname} load failed, try local")

        local_path = os.path.join(lib_dir, fname)
        if os.path.exists(local_path):
            ctypes.CDLL(local_path, mode=ctypes.RTLD_GLOBAL)
            logger.info(f"Loaded {fname} from local")
            return

        logger.warning(f"{fname} not found (system or local)")

    @classmethod
    def __load_library(cls):
        if cls._xvlib is not None:
            return
        with cls._load_lock:
            # 双重检查锁定: 防止多个线程同时加载
            if cls._xvlib is not None:
                return
            cls._check_xvsdk()
            lib_dir = os.path.dirname(__file__)

            cls._load_tbb_lib(lib_dir)
            cls._load_opencv_lib(lib_dir, 'libopencv_core.so.4.2')
            cls._load_opencv_lib(lib_dir, 'libopencv_imgproc.so.4.2')

            lib_path = os.path.abspath(os.path.join(lib_dir, 'libxvlib.so'))
            if not os.path.exists(lib_path):
                raise FileNotFoundError(f"Shared library not found: {lib_path}")
            logger.info(f"Loading library from: {lib_path}")
            cls._xvlib = ctypes.CDLL(lib_path)
            cls._configure_signatures()
            logger.info('Library initialized successfully.')

    @classmethod
    def _configure_signatures(cls):
        """为关键 C 函数设置 argtypes/restype, 避免 ctypes 类型推断错误"""
        lib = cls._xvlib
        # xv_get_devices 通过 byref 传数组指针，由 ctypes 自动推断类型
        lib.xv_get_devices.restype = ctypes.c_int
        # xv_init / xv_uninit
        lib.xv_init.argtypes = [ctypes.c_char_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_bool, ctypes.c_bool]
        lib.xv_init.restype = ctypes.c_int
        lib.xv_uninit.argtypes = [ctypes.c_int]
        lib.xv_uninit.restype = ctypes.c_int
        # xv_sleep / xv_wakeup
        lib.xv_sleep.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_sleep.restype = ctypes.c_int
        lib.xv_wakeup.argtypes = [ctypes.c_int]
        lib.xv_wakeup.restype = ctypes.c_int
        # init/uninit functions (C returns bool, must declare c_bool restype)
        _init_funcs = [
            'xv_slam_init', 'xv_slam_uninit',
            'xv_imu_sensor_init', 'xv_imu_sensor_uninit',
            'xv_event_stream_init', 'xv_event_stream_uninit',
            'xv_orientation_stream_init', 'xv_orientation_stream_uninit',
            'xv_fisheye_cameras_init', 'xv_fisheye_cameras_uninit',
            'xv_color_camera_init', 'xv_color_camera_uninit',
            'xv_tof_camera_init', 'xv_tof_camera_uninit',
            'xv_eyetracking_camera_init', 'xv_eyetracking_camera_uninit',
            'xv_gaze_stream_init', 'xv_gaze_stream_uninit',
            'xv_iris_stream_init', 'xv_iris_stream_uninit',
            'xv_gesture_stream_init', 'xv_gesture_stream_uninit',
            'xv_gps_stream_init', 'xv_gps_stream_uninit',
            'xv_gps_distance_stream_init', 'xv_gps_distance_stream_uninit',
            'xv_terrestrial_magnetism_stream_init', 'xv_terrestrial_magnetism_stream_uninit',
            'xv_external_stream_init', 'xv_external_stream_uninit',
            'xv_mic_stream_init', 'xv_mic_stream_uninit',
            'xv_object_detector_init', 'xv_object_detector_uninit',
            'xv_object_detector_RKNN3588_init', 'xv_object_detector_RKNN3588_uninit',
            'xv_device_status_stream_init', 'xv_device_status_stream_uninit',
            'xv_clamp_stream_init', 'xv_clamp_stream_uninit',
            'xv_spheretrack_stream_init', 'xv_spheretrack_stream_uninit',
        ]
        for name in _init_funcs:
            lib[name].restype = ctypes.c_bool
            lib[name].argtypes = [ctypes.c_int]
        # sgbm_camera_init has extra config string parameter
        lib.xv_sgbm_camera_init.restype = ctypes.c_bool
        lib.xv_sgbm_camera_init.argtypes = [ctypes.c_int, ctypes.c_char_p]
        lib.xv_sgbm_camera_uninit.restype = ctypes.c_bool
        lib.xv_sgbm_camera_uninit.argtypes = [ctypes.c_int]

        # data getters (return int)
        for name in ['xv_get_slam_data', 'xv_get_slam_pose', 'xv_get_slam_pose_at',
                     'xv_get_imu_sensor_data', 'xv_get_color_camera_data',
                     'xv_get_tof_camera_data', 'xv_get_fisheye_cameras_data',
                     'xv_get_eyetracking_camera_data', 'xv_get_eyetracking_camera_data_ref',
                     'xv_get_external_stream_data',
                     'xv_get_clamp_stream_data', 'xv_get_event_stream_data',
                     'xv_get_spheretrack_stream_data']:
            lib[name].restype = ctypes.c_int

        # imu / clamp / event getters (C 兼容类型)
        lib.xv_get_imu_sensor_data.argtypes = [ctypes.c_int, ctypes.c_void_p]
        lib.xv_get_imu_sensor_data.restype = ctypes.c_int
        lib.xv_get_clamp_stream_data.argtypes = [ctypes.c_int, ctypes.c_void_p]
        lib.xv_get_clamp_stream_data.restype = ctypes.c_int
        lib.xv_get_event_stream_data.argtypes = [ctypes.c_int, ctypes.c_void_p]
        lib.xv_get_event_stream_data.restype = ctypes.c_int

        # slam pose getters (额外参数)
        lib.xv_get_slam_pose.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_double]
        lib.xv_get_slam_pose_at.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_double]

        # color camera setters (argtypes)
        lib.xv_set_color_camera_rgb_mode.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_color_camera_resolution.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_color_camera_framerate.argtypes = [ctypes.c_int, ctypes.c_float]
        lib.xv_set_color_camera_brightness.argtypes = [ctypes.c_int, ctypes.c_int]

        # tof camera setters (argtypes)
        lib.xv_set_tof_camera_mode.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_tof_camera_stream_mode.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_tof_camera_distance_mode.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_tof_camera_resolution.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_tof_camera_framerate.argtypes = [ctypes.c_int, ctypes.c_float]
        lib.xv_set_tof_camera_brightness.argtypes = [ctypes.c_int, ctypes.c_int]

        # fisheye cameras setters (argtypes)
        lib.xv_set_fisheye_cameras_resolution.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_fisheye_cameras_framerate.argtypes = [ctypes.c_int, ctypes.c_float]
        lib.xv_set_fisheye_cameras_brightness.argtypes = [ctypes.c_int, ctypes.c_int]

        # eyetracking camera setters (argtypes)
        lib.xv_set_eyetracking_camera_resolution.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.xv_set_eyetracking_camera_framerate.argtypes = [ctypes.c_int, ctypes.c_float]
        lib.xv_set_eyetracking_camera_brightness.argtypes = [ctypes.c_int, ctypes.c_int]

        # 零拷贝 Ref getter (return int)
        for name in ['xv_get_color_camera_data_ref', 'xv_get_tof_camera_data_ref',
                     'xv_get_fisheye_cameras_data_ref', 'xv_get_eyetracking_camera_data_ref']:
            lib[name].restype = ctypes.c_int

        # orientation stream data getter
        lib.xv_get_orientation_stream_data.restype = ctypes.c_int
        # metadata getters
        lib.xv_get_color_image_metadata.restype = ctypes.c_int
        lib.xv_get_fisheye_metadata.restype = ctypes.c_int

    @classmethod
    def xv_get_devices(cls, timeout=5.0, max_devices=16, double_query=True):
        """Scan for connected XV devices.

        Args:
            timeout: Max seconds to wait for devices to respond.
            max_devices: Max number of device entries to return.
            double_query: If True, do a second short scan to catch late-registering
                devices (needed when multiple devices are present). Set to False
                when the caller has its own retry loop (e.g. __init__).

        Returns:
            (device_count, list_of_DeviceStruct)
        """
        cls.__load_library()
        devices = (DeviceStruct * max_devices)()
        device_count = ctypes.c_int(0)
        cls._xvlib.xv_get_devices(
            ctypes.byref(devices),
            ctypes.byref(device_count),
            ctypes.c_int(max_devices),
            ctypes.c_double(timeout)
        )
        if double_query:
            # 多设备场景下第1次扫描可能遗漏设备，第2次补扫（用独立 buffer 避免覆盖）
            if timeout > 3 and device_count.value != 0:
                time.sleep(1)
            second_devices = (DeviceStruct * max_devices)()
            second_count = ctypes.c_int(0)
            cls._xvlib.xv_get_devices(
                ctypes.byref(second_devices),
                ctypes.byref(second_count),
                ctypes.c_int(max_devices),
                ctypes.c_double(2.0)
            )
            # 合并：将第2次扫描中不在第1次结果里的设备追加进去
            first_sns = set()
            for i in range(device_count.value):
                first_sns.add(devices[i].serial)
            for i in range(second_count.value):
                sn = second_devices[i].serial
                if sn not in first_sns and device_count.value < max_devices:
                    devices[device_count.value] = second_devices[i]
                    device_count.value += 1
        return device_count.value, list(devices[:device_count.value])

    def xv_init(self, serial_number, init_slam, init_clamp_stream, init_color_camera, init_fisheye_cameras):
        """Create and initialize a device instance. Returns instance_id (>0) or INSTANCE_INVALID (-9)."""
        return self._xvlib.xv_init(serial_number, init_slam, init_clamp_stream, init_color_camera, init_fisheye_cameras)

    def xv_uninit(self):
        """Uninitialize device and release all streams. Returns 0 on success."""
        if self._xvlib is not None and self.instance_id > 0:
            return self._xvlib.xv_uninit(self.instance_id)
        else:
            return -1

    def xv_sleep(self, level=0):
        """Put device into low-power sleep mode."""
        return self._xvlib.xv_sleep(self.instance_id, level)

    def xv_wakeup(self):
        """Wake device from sleep mode."""
        return self._xvlib.xv_wakeup(self.instance_id)
    
    def xv_slam_init(self):
        """Start SLAM tracking stream. Returns True on success."""
        return self._xvlib.xv_slam_init(self.instance_id)

    def xv_slam_uninit(self):
        """Stop SLAM tracking stream. Returns True on success."""
        return self._xvlib.xv_slam_uninit(self.instance_id)

    def xv_imu_sensor_init(self):
        """Start IMU sensor stream. Returns True on success."""
        return self._xvlib.xv_imu_sensor_init(self.instance_id)

    def xv_imu_sensor_uninit(self):
        """Stop IMU sensor stream. Returns True on success."""
        return self._xvlib.xv_imu_sensor_uninit(self.instance_id)

    def xv_event_stream_init(self):
        """Start device event stream. Returns True on success."""
        return self._xvlib.xv_event_stream_init(self.instance_id)

    def xv_event_stream_uninit(self):
        """Stop device event stream. Returns True on success."""
        return self._xvlib.xv_event_stream_uninit(self.instance_id)

    def xv_orientation_stream_init(self):
        """Start 3-DOF orientation stream. Returns True on success."""
        return self._xvlib.xv_orientation_stream_init(self.instance_id)

    def xv_orientation_stream_uninit(self):
        """Stop 3-DOF orientation stream. Returns True on success."""
        return self._xvlib.xv_orientation_stream_uninit(self.instance_id)

    def xv_fisheye_cameras_init(self):
        """Start fisheye cameras stream (used for SLAM). Returns True on success."""
        return self._xvlib.xv_fisheye_cameras_init(self.instance_id)

    def xv_fisheye_cameras_uninit(self):
        """Stop fisheye cameras stream. Returns True on success."""
        return self._xvlib.xv_fisheye_cameras_uninit(self.instance_id)

    def xv_color_camera_init(self):
        """Start color (RGB) camera stream. Returns True on success."""
        return self._xvlib.xv_color_camera_init(self.instance_id)

    def xv_color_camera_uninit(self):
        """Stop color camera stream. Returns True on success."""
        return self._xvlib.xv_color_camera_uninit(self.instance_id)

    def xv_tof_camera_init(self):
        """Start TOF depth camera stream. Returns True on success."""
        return self._xvlib.xv_tof_camera_init(self.instance_id)

    def xv_tof_camera_uninit(self):
        """Stop TOF depth camera stream. Returns True on success."""
        return self._xvlib.xv_tof_camera_uninit(self.instance_id)
    
    def xv_sgbm_camera_init(self, config):
        """Start SGBM stereo depth camera stream with config string. Returns True on success."""
        return self._xvlib.xv_sgbm_camera_init(self.instance_id, ctypes.c_char_p(config.encode('utf-8')))

    def xv_sgbm_camera_uninit(self):
        """Stop SGBM camera stream. Returns True on success."""
        return self._xvlib.xv_sgbm_camera_uninit(self.instance_id)

    def xv_eyetracking_camera_init(self):
        """Start eyetracking camera stream. Returns True on success."""
        return self._xvlib.xv_eyetracking_camera_init(self.instance_id)

    def xv_eyetracking_camera_uninit(self):
        """Stop eyetracking camera stream. Returns True on success."""
        return self._xvlib.xv_eyetracking_camera_uninit(self.instance_id)

    def xv_gaze_stream_init(self):
        """Start gaze tracking stream. Returns True on success."""
        return self._xvlib.xv_gaze_stream_init(self.instance_id)

    def xv_gaze_stream_uninit(self):
        """Stop gaze tracking stream. Returns True on success."""
        return self._xvlib.xv_gaze_stream_uninit(self.instance_id)

    def xv_iris_stream_init(self):
        """Start iris recognition stream. Returns True on success."""
        return self._xvlib.xv_iris_stream_init(self.instance_id)

    def xv_iris_stream_uninit(self):
        """Stop iris recognition stream. Returns True on success."""
        return self._xvlib.xv_iris_stream_uninit(self.instance_id)

    def xv_gesture_stream_init(self):
        """Start gesture recognition stream. Returns True on success."""
        return self._xvlib.xv_gesture_stream_init(self.instance_id)

    def xv_gesture_stream_uninit(self):
        """Stop gesture recognition stream. Returns True on success."""
        return self._xvlib.xv_gesture_stream_uninit(self.instance_id)

    def xv_gps_stream_init(self):
        """Start GPS data stream. Returns True on success."""
        return self._xvlib.xv_gps_stream_init(self.instance_id)

    def xv_gps_stream_uninit(self):
        """Stop GPS data stream. Returns True on success."""
        return self._xvlib.xv_gps_stream_uninit(self.instance_id)

    def xv_gps_distance_stream_init(self):
        """Start GPS distance stream. Returns True on success."""
        return self._xvlib.xv_gps_distance_stream_init(self.instance_id)

    def xv_gps_distance_stream_uninit(self):
        """Stop GPS distance stream. Returns True on success."""
        return self._xvlib.xv_gps_distance_stream_uninit(self.instance_id)

    def xv_terrestrial_magnetism_stream_init(self):
        """Start terrestrial magnetism sensor stream. Returns True on success."""
        return self._xvlib.xv_terrestrial_magnetism_stream_init(self.instance_id)

    def xv_terrestrial_magnetism_stream_uninit(self):
        """Stop terrestrial magnetism sensor stream. Returns True on success."""
        return self._xvlib.xv_terrestrial_magnetism_stream_uninit(self.instance_id)

    def xv_external_stream_init(self):
        """Start external sensor stream. Returns True on success."""
        return self._xvlib.xv_external_stream_init(self.instance_id)

    def xv_external_stream_uninit(self):
        """Stop external sensor stream. Returns True on success."""
        return self._xvlib.xv_external_stream_uninit(self.instance_id)

    def xv_mic_stream_init(self):
        """Start microphone stream. Returns True on success."""
        return self._xvlib.xv_mic_stream_init(self.instance_id)

    def xv_mic_stream_uninit(self):
        """Stop microphone stream. Returns True on success."""
        return self._xvlib.xv_mic_stream_uninit(self.instance_id)

    def xv_object_detector_init(self):
        """Start object detector stream. Returns True on success."""
        return self._xvlib.xv_object_detector_init(self.instance_id)

    def xv_object_detector_uninit(self):
        """Stop object detector stream. Returns True on success."""
        return self._xvlib.xv_object_detector_uninit(self.instance_id)

    def xv_object_detector_RKNN3588_init(self):
        """Start object detector (RKNN3588) stream. Returns True on success."""
        return self._xvlib.xv_object_detector_RKNN3588_init(self.instance_id)

    def xv_object_detector_RKNN3588_uninit(self):
        """Stop object detector (RKNN3588) stream. Returns True on success."""
        return self._xvlib.xv_object_detector_RKNN3588_uninit(self.instance_id)

    def xv_device_status_stream_init(self):
        """Start device status stream. Returns True on success."""
        return self._xvlib.xv_device_status_stream_init(self.instance_id)

    def xv_device_status_stream_uninit(self):
        """Stop device status stream. Returns True on success."""
        return self._xvlib.xv_device_status_stream_uninit(self.instance_id)

    def xv_clamp_stream_init(self):
        """Start clamp sensor stream. Returns True on success."""
        return self._xvlib.xv_clamp_stream_init(self.instance_id)

    def xv_clamp_stream_uninit(self):
        """Stop clamp sensor stream. Returns True on success."""
        return self._xvlib.xv_clamp_stream_uninit(self.instance_id)

    def xv_spheretrack_stream_init(self):
        """Start spheretrack stream. Returns True on success."""
        return self._xvlib.xv_spheretrack_stream_init(self.instance_id)

    def xv_spheretrack_stream_uninit(self):
        """Stop spheretrack stream. Returns True on success."""
        return self._xvlib.xv_spheretrack_stream_uninit(self.instance_id)
    
    def xv_get_clamp_stream_data(self):
        """Get the most recently received clamp sensor data (updated by callback). Returns (ret_code, ClampData)."""
        ret = self._xvlib.xv_get_clamp_stream_data(self.instance_id, ctypes.byref(self._clamp_data))
        return ret, self._clamp_data

    def xv_get_event_stream_data(self):
        """Get the most recently received device event (updated by callback). Returns (ret_code, EventData)."""
        ret = self._xvlib.xv_get_event_stream_data(self.instance_id, ctypes.byref(self._event_data))
        return ret, self._event_data

    def xv_get_color_camera_data(self, use_ref=False):
        """Get the most recently received color camera image (updated by callback).

        Args:
            use_ref: If True, use zero-copy Ref API (direct SDK buffer pointer, no memcpy).
                     If False (default), use legacy API with memcpy into fixed buffer.

        Returns:
            (ret_code, ColorImageData | ColorImageDataRef). Call .frame() for an OpenCV BGR mat.
        """
        if use_ref:
            return self._xv_get_color_camera_data_ref()
        ret = self._xvlib.xv_get_color_camera_data(self.instance_id, ctypes.byref(self._color_image_data))
        return ret, self._color_image_data

    def xv_get_tof_camera_data(self, use_ref=False):
        """Get the most recently received depth/TOF camera image (updated by callback).

        Args:
            use_ref: If True, use zero-copy Ref API. Default False (legacy memcpy).

        Returns:
            (ret_code, DepthImageData | DepthImageDataRef). Call .frame() for an OpenCV mat.
        """
        if use_ref:
            return self._xv_get_tof_camera_data_ref()
        ret = self._xvlib.xv_get_tof_camera_data(self.instance_id, ctypes.byref(self._depth_image_data))
        return ret, self._depth_image_data

    def xv_get_fisheye_cameras_data(self, use_ref=False):
        """Get the most recently received fisheye camera images, up to 4 grayscale frames (updated by callback).

        Args:
            use_ref: If True, use zero-copy Ref API. Default False (legacy memcpy).

        Returns:
            (ret_code, FisheyeImagesData | FisheyeImagesDataRef). Call .frame() for a
            concatenated BGR mat, or .frame(i) for a single camera.
        """
        if use_ref:
            return self._xv_get_fisheye_cameras_data_ref()
        ret = self._xvlib.xv_get_fisheye_cameras_data(self.instance_id, ctypes.byref(self._fisheye_images_data))
        return ret, self._fisheye_images_data

    def xv_get_eyetracking_camera_data(self, use_ref=False):
        """Get the most recently received eyetracking camera images, up to 4 grayscale frames (updated by callback).

        Args:
            use_ref: If True, use zero-copy Ref API. Default False (legacy memcpy).

        Returns:
            (ret_code, EyetrackingImageData | EyetrackingImageDataRef).
        """
        if use_ref:
            return self._xv_get_eyetracking_camera_data_ref()
        ret = self._xvlib.xv_get_eyetracking_camera_data(self.instance_id, ctypes.byref(self._eyetracking_image_data))
        return ret, self._eyetracking_image_data

    def xv_get_slam_data(self):
        """Get the most recently received SLAM 6-DOF pose (updated by callback). Returns (ret_code, PoseData)."""
        ret = self._xvlib.xv_get_slam_data(self.instance_id, ctypes.byref(self._slam_data))
        return ret, self._slam_data

    def xv_get_slam_pose(self, prediction):
        """Get SLAM pose with extrapolation.

        Args:
            prediction: Seconds into the future to predict (0 = current).

        Returns:
            (ret_code, PoseData).
        """
        ret = self._xvlib.xv_get_slam_pose(self.instance_id, ctypes.byref(self._slam_data), ctypes.c_double(prediction))
        return ret, self._slam_data

    def xv_get_slam_pose_at(self, timestamp):
        """Get SLAM pose at a specific host-clock timestamp. Returns (ret_code, PoseData)."""
        ret = self._xvlib.xv_get_slam_pose_at(self.instance_id, ctypes.byref(self._slam_data), ctypes.c_double(timestamp))
        return ret, self._slam_data

    def xv_get_external_stream_data(self):
        """Get the most recently received external sensor pose (updated by callback). Returns (ret_code, PoseData)."""
        ret = self._xvlib.xv_get_external_stream_data(self.instance_id, ctypes.byref(self._external_stream_data))
        return ret, self._external_stream_data

    def xv_get_spheretrack_stream_data(self):
        """Get the most recently received spheretrack pose (updated by callback). Returns (ret_code, PoseData)."""
        ret = self._xvlib.xv_get_spheretrack_stream_data(self.instance_id, ctypes.byref(self._spheretrack_stream_data))
        return ret, self._spheretrack_stream_data

    def xv_get_orientation_stream_data(self):
        """Get the most recently received 6-DOF orientation data (quaternion + 3x3 rotation matrix).
        Returns (ret_code, OrientationData)."""
        ret = self._xvlib.xv_get_orientation_stream_data(self.instance_id, ctypes.byref(self._orientation_data))
        return ret, self._orientation_data

    def xv_get_color_image_metadata(self):
        """Get color camera image width & height (updated by callback). Returns (ret_code, width, height)."""
        width = ctypes.c_int(0)
        height = ctypes.c_int(0)
        ret = self._xvlib.xv_get_color_image_metadata(self.instance_id, ctypes.byref(width), ctypes.byref(height))
        return ret, width.value, height.value

    def xv_get_fisheye_metadata(self):
        """Get fisheye cameras image width & height arrays (updated by callback).
        Returns (ret_code, widths[4], heights[4])."""
        widths = (ctypes.c_int * 4)(0, 0, 0, 0)
        heights = (ctypes.c_int * 4)(0, 0, 0, 0)
        ret = self._xvlib.xv_get_fisheye_metadata(self.instance_id, widths, heights)
        return ret, list(widths), list(heights)

    # ============== Zero-copy Ref getters (internal, called by xv_get_*_data(use_ref=True)) ==============

    def _xv_get_color_camera_data_ref(self):
        """Internal: zero-copy color camera data (updated by callback). Returns (ret_code, ColorImageDataRef)."""
        ret = self._xvlib.xv_get_color_camera_data_ref(self.instance_id, ctypes.byref(self._color_image_data_ref))
        return ret, self._color_image_data_ref

    def _xv_get_tof_camera_data_ref(self):
        """Internal: zero-copy depth camera data (updated by callback). Returns (ret_code, DepthImageDataRef)."""
        ret = self._xvlib.xv_get_tof_camera_data_ref(self.instance_id, ctypes.byref(self._depth_image_data_ref))
        return ret, self._depth_image_data_ref

    def _xv_get_fisheye_cameras_data_ref(self):
        """Internal: zero-copy fisheye camera data (updated by callback). Returns (ret_code, FisheyeImagesDataRef)."""
        ret = self._xvlib.xv_get_fisheye_cameras_data_ref(self.instance_id, ctypes.byref(self._fisheye_images_data_ref))
        return ret, self._fisheye_images_data_ref

    def _xv_get_eyetracking_camera_data_ref(self):
        """Internal: zero-copy eyetracking camera data (updated by callback). Returns (ret_code, EyetrackingImageDataRef)."""
        ret = self._xvlib.xv_get_eyetracking_camera_data_ref(self.instance_id, ctypes.byref(self._eyetracking_image_data_ref))
        return ret, self._eyetracking_image_data_ref

    # ============================================================================================

    def xv_set_color_camera_rgb_mode(self, mode):
        """Set color camera RGB mode. 0=AF, 1=MF, 2=Unknown. Returns ret_code."""
        return self._xvlib.xv_set_color_camera_rgb_mode(self.instance_id, ctypes.c_int(mode))

    def xv_set_color_camera_resolution(self, resolution):
        """Set color camera resolution. 0=1920x1080, 1=1280x720, 2=640x480, 3=320x240, 4=2560x1920, 5=3840x2160. Returns ret_code."""
        return self._xvlib.xv_set_color_camera_resolution(self.instance_id, ctypes.c_int(resolution))

    def xv_set_color_camera_framerate(self, framerate):
        """Set color camera framerate (float, Hz). Returns ret_code."""
        return self._xvlib.xv_set_color_camera_framerate(self.instance_id, ctypes.c_float(framerate))

    def xv_set_color_camera_brightness(self, brightness):
        """Set color camera brightness. Returns ret_code."""
        return self._xvlib.xv_set_color_camera_brightness(self.instance_id, ctypes.c_int(brightness))

    def xv_set_tof_camera_mode(self, mode):
        """Set TOF camera mode. Returns ret_code."""
        return self._xvlib.xv_set_tof_camera_mode(self.instance_id, ctypes.c_int(mode))

    def xv_set_tof_camera_stream_mode(self, mode):
        """Set TOF stream mode. 0=DepthOnly, 1=CloudOnly, 2=DepthAndCloud, 3=None, 4=CloudOnLeftHandSlam. Returns ret_code."""
        return self._xvlib.xv_set_tof_camera_stream_mode(self.instance_id, ctypes.c_int(mode))

    def xv_set_tof_camera_distance_mode(self, mode):
        """Set TOF distance mode. 0=Short, 1=Middle, 2=Long. Returns ret_code."""
        return self._xvlib.xv_set_tof_camera_distance_mode(self.instance_id, ctypes.c_int(mode))

    def xv_set_tof_camera_resolution(self, resolution):
        """Set TOF camera resolution. -1=Unknown, 0=VGA, 1=QVGA, 2=HQVGA. Returns ret_code."""
        return self._xvlib.xv_set_tof_camera_resolution(self.instance_id, ctypes.c_int(resolution))

    def xv_set_tof_camera_framerate(self, framerate):
        """Set TOF camera framerate (float, Hz, e.g. 5.0, 10.0, 15.0, 20.0, 25.0, 30.0). Returns ret_code."""
        return self._xvlib.xv_set_tof_camera_framerate(self.instance_id, ctypes.c_float(framerate))

    def xv_set_tof_camera_brightness(self, brightness):
        """Set TOF camera brightness. Returns ret_code."""
        return self._xvlib.xv_set_tof_camera_brightness(self.instance_id, ctypes.c_int(brightness))

    def xv_set_fisheye_cameras_resolution(self, resolution):
        """Set fisheye cameras resolution. Returns ret_code."""
        return self._xvlib.xv_set_fisheye_cameras_resolution(self.instance_id, ctypes.c_int(resolution))

    def xv_set_fisheye_cameras_framerate(self, framerate):
        """Set fisheye cameras framerate (float, Hz). Returns ret_code."""
        return self._xvlib.xv_set_fisheye_cameras_framerate(self.instance_id, ctypes.c_float(framerate))

    def xv_set_fisheye_cameras_brightness(self, brightness):
        """Set fisheye cameras brightness. Returns ret_code."""
        return self._xvlib.xv_set_fisheye_cameras_brightness(self.instance_id, ctypes.c_int(brightness))

    def xv_set_eyetracking_camera_resolution(self, resolution):
        """Set eyetracking camera resolution. Returns ret_code."""
        return self._xvlib.xv_set_eyetracking_camera_resolution(self.instance_id, ctypes.c_int(resolution))

    def xv_set_eyetracking_camera_framerate(self, framerate):
        """Set eyetracking camera framerate (float, Hz). Returns ret_code."""
        return self._xvlib.xv_set_eyetracking_camera_framerate(self.instance_id, ctypes.c_float(framerate))

    def xv_set_eyetracking_camera_brightness(self, brightness):
        """Set eyetracking camera brightness. Returns ret_code."""
        return self._xvlib.xv_set_eyetracking_camera_brightness(self.instance_id, ctypes.c_int(brightness))
