import logging
import threading

import customtkinter as ctk

from util.camera_device import CameraDevice

logger = logging


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        logger.info('Main Thread %s', threading.Thread.name)
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme("green")
        self.geometry('1000x600')
        self.title('Camera Application')
        self.minsize(800, 500)

        self.canvas_width = self.winfo_width()
        self.canvas_height = self.winfo_height()

        self.button_frame = ctk.CTkFrame(self)
        self.camera_switch_var = ctk.StringVar(value='ON')
        self.camera_switch = ctk.CTkSwitch(self.button_frame, text='Camera', onvalue='ON', offvalue='OFF',
                                           variable=self.camera_switch_var, command=self.switch_camera)
        self.camera_switch.pack(side='right', padx=20, pady=20)
        self.button_frame.pack(expand=False, fill='x', side='top')

        self.preview_frame = ctk.CTkFrame(self)
        self.preview_label_var = ctk.StringVar()
        self.preview_label = ctk.CTkLabel(self.preview_frame, textvariable=self.preview_label_var)
        self.preview_label.pack(expand=True, fill='both')

        self.preview_frame.pack(expand=True, fill='both', side='top')
        self.preview_frame.bind('<Configure>', self.image_resize_func)

        self.camera_enable = ctk.BooleanVar(value=True)
        self.camera_device = CameraDevice(self.camera_enable, self.update_camera_image)
        self.camera_device.set_camera_status_callback(self.update_device_status)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.mainloop()
        print('Closed!')

    def on_closing(self):
        self.camera_device.stop()
        self.destroy()

    def image_resize_func(self, event):
        logger.info('Resize function called!')
        self.canvas_width = event.width
        self.canvas_height = event.height

    def update_camera_image(self, image):
        if not self.camera_enable.get():
            logger.warning('Frame received from camera, but camera is disabled!')
            self.preview_label.configure(image=None)
            return

        if image and self.canvas_width and self.canvas_height:
            window_ratio = self.canvas_width / self.canvas_height
            image_ratio = image.width / image.height

            if image_ratio > window_ratio:
                image_width = self.canvas_width
                image_height = self.canvas_width / image_ratio
            else:
                image_width = (self.canvas_height * image_ratio)
                image_height = self.canvas_height

            photo_image = ctk.CTkImage(image, size=(image_width, image_height))
            self.preview_label_var.set('')
            self.preview_label.configure(image=photo_image)
        else:
            self.preview_label.configure(image=None)

    def update_camera_preview_description(self):
        if not self.camera_enable.get():
            self.preview_label_var.set('Camera Disabled!')
        else:
            if not self.camera_device.is_camera_available():
                self.preview_label_var.set('Camera not available!')
            else:
                self.preview_label_var.set('')

    def switch_camera(self, *args):
        self.camera_enable.set(self.camera_switch_var.get() == 'ON')
        self.update_camera_preview_description()

    def update_device_status(self, available):
        self.update_camera_preview_description()


if __name__ == '__main__':
    threading.Thread.name = 'main'
    App()
