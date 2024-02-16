import time
from PIL import Image
import cv2
import pyudev
import logging
import customtkinter as ctk
import threading

logger = logging


class CameraDevice:
    def __init__(self, camera_enable_flag, frame_capture_callback, max_frame_rate=20):
        self.camera_enable_flag = camera_enable_flag
        self.frame_capture_callback = frame_capture_callback
        self.camera_device_callback = None

        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb')
        self.observer = pyudev.MonitorObserver(self.monitor, self.usb_device_event_handler)

        self.active = True
        self.vid = None
        self.image = None
        self.image_update_flag = ctk.BooleanVar()
        self.image_update_flag.trace('w', self.image_received)

        self.max_frame_rate = max_frame_rate
        self.min_frame_interval = 1000000000.0 / self.max_frame_rate
        logger.info(f'Frame interval {self.min_frame_interval} ns')
        self.terminate_camera_thread = None
        self.cameraThread = None

        self.camera_enable_flag.trace('w', self.update_camera_enable_flag)
        self.try_start_camera()
        self.observer.start()

    def set_camera_status_callback(self, camera_status_callback):
        self.camera_device_callback = camera_status_callback

    def is_camera_available(self):
        return self.vid is not None

    def image_received(self, *args):
        self.frame_capture_callback(self.image)

    def update_camera_enable_flag(self, *args):
        if self.camera_enable_flag.get():
            self.try_start_camera()

    def try_start_camera(self):
        logger.info('Try to start capture')
        if self.vid is None:
            video = cv2.VideoCapture(0)
            if video.isOpened:
                logger.info('Camera device available')
                self.vid = video
                self.terminate_camera_thread = threading.Event()
                self.cameraThread = threading.Thread(target=self.open_camera, daemon=True)
                self.cameraThread.start()
                if self.camera_device_callback:
                    self.camera_device_callback(True)
        else:
            logger.info('Already capturing')

    def stop(self):
        self.active = False
        if self.terminate_camera_thread:
            self.terminate_camera_thread.set()

        if self.vid and self.vid.isOpened:
            self.vid.release()
            self.vid = None
        logger.info(f'Camera Thread alive {self.cameraThread.is_alive()}')

    def usb_device_event_handler(self, action, device):
        print(f'{action} {device.device_number}')
        if action == 'bind' and (not device.device_number == 0) and self.vid is None:
            print(f'Trying to open video capture {device.device_number}')
            self.try_start_camera()

    def open_camera(self):
        logger.info('Start Capturing from Camera')
        last_frame_time = time.monotonic_ns()
        try:
            while not self.terminate_camera_thread.is_set():
                if not self.camera_enable_flag.get():
                    logger.info('Camera disabled')
                    break
                logger.debug('Reading image from video')
                ret, frame = self.vid.read()
                if not ret:
                    logger.info('Camera stream not available, Releasing camera')
                    break
                if self.active:
                    time_ns = time.monotonic_ns()
                    if (time_ns - last_frame_time) < self.min_frame_interval:
                        pass
                    else:
                        last_frame_time = time_ns
                        logger.debug('Creating Image')
                        opencv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                        captured_image = Image.fromarray(cv2.flip(opencv_image, 1))
                        self.image = captured_image
                        logger.debug('Update flag')
                        self.image_update_flag.set(True)
                        logger.debug('Flag updated')
        except Exception as e:
            logger.exception('Failed ')
        logger.info("Releasing camera")
        if self.vid:
            self.vid.release()
        self.vid = None
        self.image = None
        if self.active:
            self.image_update_flag.set(False)

        if self.camera_device_callback:
            self.camera_device_callback(False)
        logger.info("Stop Camera Capturing Thread")
