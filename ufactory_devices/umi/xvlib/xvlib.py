import os
import ctypes
import cv2
import time
import logging
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('uf.xvlib')


class DeviceStruct(ctypes.Structure):
    _fields_ = [
        ("uuid", ctypes.c_char * 100)
    ]
    
    @property
    def serial_number(self):
        return self.uuid.decode('utf-8')


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
    _fields_ = [
        ("timestamp", ctypes.c_double),
        ("data", ctypes.c_double)
    ]


class ColorImageData(ctypes.Structure):
    _fields_ = [
        ("codec", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("data", ctypes.c_uint8 * int(1280*1280*3)),
        ("dataSize", ctypes.c_uint),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong)
    ]
    def frame(self, rgb=False):
        np_array = np.frombuffer(bytes(self.data[:self.dataSize]), dtype=np.uint8)
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
        return frame


class DepthImageData(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("confidence", ctypes.c_double),
        ("data", ctypes.c_uint8 * int(1280*1280*3)),
        ("dataSize", ctypes.c_uint),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong)
    ]
    def frame(self):
        np_array = np.frombuffer(bytes(self.data[:self.dataSize]), dtype=np.uint8)
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
                raise ValueError("IR 数据长度不匹配")
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
        return frame


class RgbImageData(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("data", ctypes.c_uint8 * (1280*1280*3)),
        ("dataSize", ctypes.c_uint),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong)
    ]
    def frame(self, rgb=False):
        rgb_frame = np.frombuffer(bytes(self.data[:self.dataSize]), dtype=np.uint8).reshape((self.height, self.width, 3))
        if rgb:
            return rgb_frame.copy()
        # RGB => BGR
        return cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)  # 转换颜色空间


class GrayScaleImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("data", ctypes.c_uint8 * (640*480))
    ]
    def frame(self):
        buf_size = 640 * 480
        count = min(self.width * self.height, buf_size)
        return np.array(self.data[:count], dtype=np.uint8).reshape((self.height, self.width, 1))


class FisheyeImagesData(ctypes.Structure):
    _fields_ = [
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("images", GrayScaleImage * 4),
        ("id", ctypes.c_longlong)
    ]

    def frame(self, inx=-1):
        inx_vaild = inx >= 0 and inx < 4
        if inx_vaild:
            return self.images[inx].frame()
        else:
            frame0 = cv2.resize(self.images[0].frame(), (480, 360))
            frame1 = cv2.resize(self.images[1].frame(), (480, 360))
            frame2 = cv2.resize(self.images[2].frame(), (480, 360))
            frame3 = cv2.resize(self.images[3].frame(), (480, 360))

            up_frame = cv2.hconcat([frame0, frame1])
            down_frame = cv2.hconcat([frame2, frame3])
            return cv2.vconcat([up_frame, down_frame])


class EyetrackingImageData(ctypes.Structure):
    _fields_ = [
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("images", GrayScaleImage * 4),
    ]


class PoseData(ctypes.Structure):
    _fields_ = [
        ("position", Vector3D),
        ("orientation", Vector3D),
        ("quaternion", Vector4D),
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("confidence", ctypes.c_double)
    ]


class ImuData(ctypes.Structure):
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
    _fields_ = [
        ("hostTimestamp", ctypes.c_double),
        ("edgeTimestampUs", ctypes.c_longlong),
        ("type", ctypes.c_int),
        ("state", ctypes.c_int)
    ]


class XVLib:
    _xvlib = None

    def __init__(self, serial_number, init_slam=False, init_clamp_stream=False, init_color_camera=False, init_fisheye_cameras=False):
        self.instance_id = -1

        self._clamp_data = ClampData()
        self._color_image_data = ColorImageData()
        self._color_image_rgb_data = RgbImageData()
        self._depth_image_data = DepthImageData()
        self._fisheye_images_data = FisheyeImagesData()
        self._slam_data = PoseData()
        self._external_stream_data = PoseData()
        self._spheretrack_stream_data = PoseData()

        self.xv_get_devices()
        time.sleep(1)

        serial_number = ctypes.c_char_p(serial_number.encode('utf-8'))
        self.instance_id = self.xv_init(serial_number, init_slam, init_clamp_stream, init_color_camera, init_fisheye_cameras)
        if self.instance_id > 0:
            logger.info('Device initialized successfully.')
        else:
            raise Exception('Device initialized failure.')
    
    def __del__(self):
        self.xv_uninit()
    
    @classmethod
    def __load_library(cls):
        if cls._xvlib is None:
            # 加载动态库
            lib_dir = os.path.dirname(__file__)
            if os.path.exists(os.path.join(lib_dir, 'libopencv_core.so.4.2')):
                ctypes.CDLL(os.path.join(lib_dir, 'libopencv_core.so.4.2'), mode=ctypes.RTLD_GLOBAL)
            if os.path.exists(os.path.join(lib_dir, 'libopencv_imgproc.so.4.2')):
                ctypes.CDLL(os.path.join(lib_dir, 'libopencv_imgproc.so.4.2'), mode=ctypes.RTLD_GLOBAL)
            lib_path = os.path.abspath(os.path.join(lib_dir, 'libxvlib.so'))
            logger.info(f"Loading library from: {lib_path}")
            cls._xvlib = ctypes.CDLL(lib_path)
            logger.info('Library initialized successfully.')

    @classmethod
    def xv_get_devices(cls, max_devices=16):
        cls.__load_library()
        devices = (DeviceStruct * max_devices)()
        device_count = ctypes.c_int(0)
        cls._xvlib.xv_get_devices(
            ctypes.byref(devices),
            ctypes.byref(device_count),
            ctypes.c_int(max_devices)
        )
        return device_count.value, list(devices[:device_count.value])

    def xv_init(self, serial_number, init_slam, init_clamp_stream, init_color_camera, init_fisheye_cameras):
        return self._xvlib.xv_init(serial_number, init_slam, init_clamp_stream, init_color_camera, init_fisheye_cameras)

    def xv_uninit(self):
        if self._xvlib is not None and self.instance_id > 0:
            return self._xvlib.xv_uninit(self.instance_id)
        else:
            return -1
    
    def xv_sleep(self, level = 0):
        return self._xvlib.xv_sleep(self.instance_id, level)

    def xv_wakeup(self):
        return self._xvlib.xv_wakeup(self.instance_id) 
    
    def xv_slam_init(self):
        return self._xvlib.xv_slam_init(self.instance_id)

    def xv_slam_uninit(self):
        return self._xvlib.xv_slam_uninit(self.instance_id)
    
    def xv_imu_sensor_init(self):
        return self._xvlib.xv_imu_sensor_init(self.instance_id)

    def xv_imu_sensor_uninit(self):
        return self._xvlib.xv_imu_sensor_uninit(self.instance_id)
    
    def xv_event_stream_init(self):
        return self._xvlib.xv_event_stream_init(self.instance_id)

    def xv_event_stream_uninit(self):
        return self._xvlib.xv_event_stream_uninit(self.instance_id)
    
    def xv_orientation_stream_init(self):
        return self._xvlib.xv_orientation_stream_init(self.instance_id)

    def xv_orientation_stream_uninit(self):
        return self._xvlib.xv_orientation_stream_uninit(self.instance_id)
    
    def xv_fisheye_cameras_init(self):
        return self._xvlib.xv_fisheye_cameras_init(self.instance_id)

    def xv_fisheye_cameras_uninit(self):
        return self._xvlib.xv_fisheye_cameras_uninit(self.instance_id)
    
    def xv_color_camera_init(self):
        return self._xvlib.xv_color_camera_init(self.instance_id)
    
    def xv_color_camera_uninit(self):
        return self._xvlib.xv_color_camera_uninit(self.instance_id)

    def xv_tof_camera_init(self):
        return self._xvlib.xv_tof_camera_init(self.instance_id)
    
    def xv_tof_camera_uninit(self):
        return self._xvlib.xv_tof_camera_uninit(self.instance_id)
    
    def xv_sgbm_camera_init(self, config):
        return self._xvlib.xv_sgbm_camera_init(self.instance_id, ctypes.c_char_p(config.encode('utf-8')))
    
    def xv_sgbm_camera_uninit(self):
        return self._xvlib.xv_sgbm_camera_uninit(self.instance_id)
    
    def xv_eyetracking_camera_init(self):
        return self._xvlib.xv_eyetracking_camera_init(self.instance_id)
    
    def xv_eyetracking_camera_uninit(self):
        return self._xvlib.xv_eyetracking_camera_uninit(self.instance_id)

    def xv_gaze_stream_init(self):
        return self._xvlib.xv_gaze_stream_init(self.instance_id)
    
    def xv_gaze_stream_uninit(self):
        return self._xvlib.xv_gaze_stream_uninit(self.instance_id)
    
    def xv_iris_stream_init(self):
        return self._xvlib.xv_iris_stream_init(self.instance_id)
    
    def xv_iris_stream_uninit(self):
        return self._xvlib.xv_iris_stream_uninit(self.instance_id)
    
    def xv_gesture_stream_init(self):
        return self._xvlib.xv_gesture_stream_init(self.instance_id)
    
    def xv_gesture_stream_uninit(self):
        return self._xvlib.xv_gesture_stream_uninit(self.instance_id)
    
    def xv_gps_stream_init(self):
        return self._xvlib.xv_gps_stream_init(self.instance_id)
    
    def xv_gps_stream_uninit(self):
        return self._xvlib.xv_gps_stream_uninit(self.instance_id)
    
    def xv_gps_distance_stream_init(self):
        return self._xvlib.xv_gps_distance_stream_init(self.instance_id)
    
    def xv_gps_distance_stream_uninit(self):
        return self._xvlib.xv_gps_distance_stream_uninit(self.instance_id)
    
    def xv_terrestrial_magnetism_stream_init(self):
        return self._xvlib.xv_terrestrial_magnetism_stream_init(self.instance_id)
    
    def xv_terrestrial_magnetism_stream_uninit(self):
        return self._xvlib.xv_terrestrial_magnetism_stream_uninit(self.instance_id)

    def xv_external_stream_init(self):
        return self._xvlib.xv_external_stream_init(self.instance_id)

    def xv_external_stream_uninit(self):
        return self._xvlib.xv_external_stream_uninit(self.instance_id)
    
    def xv_mic_stream_init(self):
        return self._xvlib.xv_mic_stream_init(self.instance_id)

    def xv_mic_stream_uninit(self):
        return self._xvlib.xv_mic_stream_uninit(self.instance_id)
    
    def xv_object_detector_init(self):
        return self._xvlib.xv_object_detector_init(self.instance_id)

    def xv_object_detector_uninit(self):
        return self._xvlib.xv_object_detector_uninit(self.instance_id)
    
    def xv_object_detector_RKNN3588_init(self):
        return self._xvlib.xv_object_detector_RKNN3588_init(self.instance_id)

    def xv_object_detector_RKNN3588_uninit(self):
        return self._xvlib.xv_object_detector_RKNN3588_uninit(self.instance_id)
    
    def xv_device_status_stream_init(self):
        return self._xvlib.xv_device_status_stream_init(self.instance_id)

    def xv_device_status_stream_uninit(self):
        return self._xvlib.xv_device_status_stream_uninit(self.instance_id)

    def xv_clamp_stream_init(self):
        return self._xvlib.xv_clamp_stream_init(self.instance_id)
    
    def xv_clamp_stream_uninit(self):
        return self._xvlib.xv_clamp_stream_uninit(self.instance_id)
    
    def xv_spheretrack_stream_init(self):
        return self._xvlib.xv_spheretrack_stream_init(self.instance_id)

    def xv_spheretrack_stream_uninit(self):
        return self._xvlib.xv_spheretrack_stream_uninit(self.instance_id)
    
    def xv_get_clamp_stream_data(self):
        ret = self._xvlib.xv_get_clamp_stream_data(self.instance_id, ctypes.byref(self._clamp_data))
        return ret, self._clamp_data
    
    def xv_get_color_image_data(self):
        ret = self._xvlib.xv_get_color_image_data(self.instance_id, ctypes.byref(self._color_image_data))
        return ret, self._color_image_data

    def xv_get_color_image_rgb_data(self):
        ret = self._xvlib.xv_get_color_image_rgb_data(self.instance_id, ctypes.byref(self._color_image_rgb_data))
        return ret, self._color_image_rgb_data
    
    def xv_get_depth_image_data(self):
        ret = self._xvlib.xv_get_depth_image_data(self.instance_id, ctypes.byref(self._depth_image_data))
        return ret, self._depth_image_data

    def xv_get_fisheye_images_data(self, index=5):
        ret = self._xvlib.xv_get_fisheye_images_data(self.instance_id, ctypes.byref(self._fisheye_images_data), ctypes.c_size_t(index))
        return ret, self._fisheye_images_data
    
    def xv_get_slam_data(self):
        ret = self._xvlib.xv_get_slam_data(self.instance_id, ctypes.byref(self._slam_data))
        return ret, self._slam_data
    
    def xv_get_slam_pose(self, prediction):
        ret = self._xvlib.xv_get_slam_pose(self.instance_id, ctypes.byref(self._slam_data), ctypes.c_double(prediction))
        return ret, self._slam_data
    
    def xv_get_slam_pose_at(self, timestamp):
        ret = self._xvlib.xv_get_slam_pose_at(self.instance_id, ctypes.byref(self._slam_data), ctypes.c_double(timestamp))
        return ret, self._slam_data
    
    def xv_get_external_stream_data(self):
        ret = self._xvlib.xv_get_external_stream_data(self.instance_id, ctypes.byref(self._external_stream_data))
        return ret, self._external_stream_data
    
    def xv_get_spheretrack_stream_data(self):
        ret = self._xvlib.xv_get_spheretrack_stream_data(self.instance_id, ctypes.byref(self._spheretrack_stream_data))
        return ret, self._spheretrack_stream_data
    
    def xv_set_color_camera_rgb_mode(self, mode):
        """
        Docstring for xv_set_color_camera_rgb_mode
        
        :param mode: Description
            0: AF
            1: MF
            2: Unknown
        """
        return self._xvlib.xv_set_color_camera_rgb_mode(self.instance_id, ctypes.c_int(mode))
    
    def xv_set_color_camera_resolution(self, resolution):
        """
        Docstring for xv_set_color_camera_resolution
        
        :param resolution: 
            0: RGB_1920x1080
            1: RGB_1280x720
            2: RGB_640x480
            3: RGB_320x240 (not supported now)
            4: RGB_2560x1920 (not supported now)
            5: RGB_3840x2160 (not supported now)
        """
        return self._xvlib.xv_set_color_camera_resolution(self.instance_id, ctypes.c_int(resolution))
    
    def xv_set_color_camera_framerate(self, framerate):
        return self._xvlib.xv_set_color_camera_framerate(self.instance_id, ctypes.c_float(framerate))
    
    def xv_set_color_camera_brightness(self, brightness):
        return self._xvlib.xv_set_color_camera_brightness(self.instance_id, ctypes.c_int(brightness))
    
    def xv_set_tof_camera_mode(self, mode):
        return self._xvlib.xv_set_tof_camera_mode(self.instance_id, ctypes.c_int(mode))
    
    def xv_set_tof_camera_stream_mode(self, mode):
        """
        Docstring for xv_set_tof_camera_stream_mode
        
        :param mode: Description
            0: DepthOnly
            1: CloudOnly
            2: DepthAndCloud
            3: None
            4: CloudOnLeftHandSlam
        """
        return self._xvlib.xv_set_tof_camera_stream_mode(self.instance_id, ctypes.c_int(mode))
    
    def xv_set_tof_camera_distance_mode(self, mode):
        """
        Docstring for xv_set_tof_camera_distance_mode
        
        :param mode: Description
            0: Short
            1: Middle
            2: Long
        """
        return self._xvlib.xv_set_tof_camera_distance_mode(self.instance_id, ctypes.c_int(mode))

    def xv_set_tof_camera_resolution(self, resolution):
        """
        Docstring for xv_set_tof_camera_resolution
        
        :param resolution: Description
            -1: Unknown
            0: VGA
            1: QVGA
            2: HQVGA
        """
        return self._xvlib.xv_set_tof_camera_resolution(self.instance_id, ctypes.c_int(resolution))
    
    def xv_set_tof_camera_framerate(self, framerate):
        """
        Docstring for xv_set_tof_camera_framerate
        
        :param framerate: Description
            0: FPS_5
            1: FPS_10
            2: FPS_15
            3: FPS_20
            4: FPS_25
            5: FPS_30
        """
        return self._xvlib.xv_set_tof_camera_framerate(self.instance_id, ctypes.c_float(framerate))
    
    def xv_set_tof_camera_brightness(self, brightness):
        return self._xvlib.xv_set_tof_camera_brightness(self.instance_id, ctypes.c_int(brightness))
    
    def xv_set_fisheye_cameras_resolution(self, resolution):
        return self._xvlib.xv_set_fisheye_cameras_resolution(self.instance_id, ctypes.c_int(resolution))
    
    def xv_set_fisheye_cameras_framerate(self, framerate):
        return self._xvlib.xv_set_fisheye_cameras_framerate(self.instance_id, ctypes.c_float(framerate))

    def xv_set_fisheye_cameras_brightness(self, brightness):
        return self._xvlib.xv_set_fisheye_cameras_brightness(self.instance_id, ctypes.c_int(brightness))

    def xv_set_eyetracking_camera_resolution(self, resolution):
        return self._xvlib.xv_set_eyetracking_camera_resolution(self.instance_id, ctypes.c_int(resolution))
    
    def xv_set_eyetracking_camera_framerate(self, framerate):
        return self._xvlib.xv_set_eyetracking_camera_framerate(self.instance_id, ctypes.c_float(framerate))
    
    def xv_set_eyetracking_camera_brightness(self, brightness):
        return self._xvlib.xv_set_eyetracking_camera_brightness(self.instance_id, ctypes.c_int(brightness))
