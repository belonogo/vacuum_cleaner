from subprocess import call
import threading
import time
import wiring_controls as wc
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.base import stopTouchApp


class BaseScreen(Screen):

    def __init__(self, **kwargs):
        super(BaseScreen, self).__init__(**kwargs)

    def on_stop(self):
        app.wc.stop_all()



class BrushScreen(Screen):

    def __init__(self, **kwargs):
        super(BrushScreen, self).__init__(**kwargs)
        self.wc = app.wc
        # If vacuum cleaner is working or not
        self.vacuum_cleaner_state = 0
        self.brush = False
        self.water = False
        threading.Thread(target=self.body_state_thread).start()
        threading.Thread(target=self.joystick_thread).start()

    def on_brush_speed_value(self, instance, value):
        value = value / instance.max * wc.PWM_DC_RANGE
        self.wc.set_pwm_dc(wc.BRUSH_PIN, int(value))

    # Movement of the brushes (up, down, pull apart, bring closer)
    def on_brush_move_press(self, direction):
        # When the button is pressed
        if direction == "UP":
            self.wc.digital_write(wc.BRUSH_DOWN_PIN, 0)
            self.wc.digital_write(wc.BRUSH_UP_PIN, 1)
        elif direction == "DOWN":
            self.wc.digital_write(wc.BRUSH_UP_PIN, 0)
            self.wc.digital_write(wc.BRUSH_DOWN_PIN, 1)
        elif direction == "CLOSE":
            self.wc.digital_write(wc.BRUSH_APART_PIN, 0)
            self.wc.digital_write(wc.BRUSH_CLOSE_PIN, 1)
        elif direction == "APART":
            self.wc.digital_write(wc.BRUSH_CLOSE_PIN, 0)
            self.wc.digital_write(wc.BRUSH_APART_PIN, 1)

    def on_brush_move_release(self, direction):
        # When the button is released
        if direction == "UP":
            self.wc.digital_write(wc.BRUSH_UP_PIN, 0)
        elif direction == "DOWN":
            self.wc.digital_write(wc.BRUSH_DOWN_PIN, 0)
        elif direction == "CLOSE":
            self.wc.digital_write(wc.BRUSH_CLOSE_PIN, 0)
        elif direction == "APART":
            self.wc.digital_write(wc.BRUSH_APART_PIN, 0)

    # Switch vacuum cleaner state if possible
    def on_vacuum_cleaner_button_release(self):
        if self.vacuum_cleaner_state == 0 and app.body_is_up == 0:
            # We can only enable it
            # if the vacuum cleaner is disabled and the body is down.
            self.wc.digital_write(wc.VACUUM_CLEANER_SWITCH_PIN, 1)
            self.vacuum_cleaner_state = 1
            self.ids.vacuum_cleaner_button.background_normal = "Graphics/Brush/Vacuum_button_pressed.tif"
        elif self.vacuum_cleaner_state == 1:
            # If the vacuum cleaner is enabled,
            # then we can disable it regardless of the body state.
            self.wc.digital_write(wc.VACUUM_CLEANER_SWITCH_PIN, 0)
            self.vacuum_cleaner_state = 0
            self.ids.vacuum_cleaner_button.background_normal = "Graphics/Brush/Vacuum_button_normal.tif"

    # Separate thread for disabling vacuum cleaner on body_is_up
    def body_state_thread(self):
        while not app.stop_event.is_set():
            if app.body_is_up and self.vacuum_cleaner_state:
                # if the body is up, the vacuum cleaner must be disabled.
                self.on_vacuum_cleaner_switch_release()
            time.sleep(0.1)  # in seconds

    def joystick_thread(self):
        pins = [wc.JOYSTICK_UP_PIN, wc.JOYSTICK_DOWN_PIN, wc.JOYSTICK_LEFT_PIN, wc.JOYSTICK_RIGHT_PIN]
        dirs = ["UP", "DOWN", "CLOSE", "APART"]
        while not app.stop_event.is_set():
            for i in range(len(pins)):
                pin = pins[i]
                if self.wc.digital_read(pin):
                    dir = dirs[i]
                    self.on_brush_move_press(dir)
                    while not app.stop_event.is_set() and self.wc.digital_read(pin):
                        time.sleep(0.05)
                    if not app.stop_event.is_set():
                        self.on_brush_move_release(dir)

    def on_brush_button_release(self):
        print("Brush button pressed!")
        if self.brush is True:
            self.brush = False
            self.wc.digital_write(wc.BRUSH_SWITCH_PIN, 0)
            print("brush written 0")
            self.ids.brush_button.background_normal = "Graphics/Brush/Brush_button_normal.tif"
        else:
            self.brush = True
            self.wc.digital_write(wc.BRUSH_SWITCH_PIN, 1)
            print("brush written 1")
            self.ids.brush_button.background_normal = "Graphics/Brush/Brush_button_pressed.tif"

    def on_water_button_release(self):
        print("Water button pressed!")
        if self.water is True:
            self.water = False
            self.wc.digital_write(wc.WATER_SWITCH_PIN, 0)
            print("Water written 0")
            self.ids.water_button.background_normal = "Graphics/Brush/Water_button_normal.tif"
        else:
            self.water = True
            self.wc.digital_write(wc.WATER_SWITCH_PIN, 1)
            print("Water written 1")
            self.ids.water_button.background_normal = "Graphics/Brush/Water_button_pressed.tif"


class CleanerApp(App):
    stop_event = threading.Event()
    shutdown = False

    def set_stop(self):
        self.stop_event.set()

    def on_stop(self):
        self.root.get_screen('base').on_stop()
        self.root.get_screen('camera').on_stop()
        self.root.get_screen('settings').on_stop()
        if self.shutdown is True:
            call("sudo shutdown -h now", shell=False)

    def power_off(self):
        self.set_stop()
        self.shutdown = True
        if self.shutdown is True:
            call("sudo shutdown -h now", shell=True)
        stopTouchApp()

    def build(self):
        self.wc = wc.WiringControls()
        self.body_is_up = 1
        screen_manager = ScreenManager()
        screen_manager.add_widget(BaseScreen(name='base'))
        return screen_manager


if __name__ == '__main__':
    Window.fullscreen = True
    app = CleanerApp()
    try:
        app.run()
    except:
        # In case of an exception raised, try to disable all pins
        app.wc.stop_all()
        # and release the camera device.
        app.root.get_screen('camera').capture.release()
        raise
