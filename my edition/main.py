from functools import partial
from subprocess import call
import threading
import time
import cv2
import wiring_controls as wc
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.clock import mainthread, Clock
from kivy.graphics.texture import Texture
from kivy.base import stopTouchApp

from kivy.uix.scatter import Scatter
from kivy.properties import NumericProperty, BoundedNumericProperty, StringProperty
from kivy.animation import Animation



class BaseScreen(Screen):

    def __init__(self, **kwargs):
        super(BaseScreen, self).__init__(**kwargs)

    def on_stop(self):
        app.wc.stop_all()

class SensorScreen(Screen):

    def __init__(self, **kwargs):
        super(SensorScreen, self).__init__(**kwargs)
        self.wc = app.wc
        threading.Thread(target=self.speedometer_thread).start()
        threading.Thread(target=self.sensors_thread).start()

    @mainthread
    def update_speedometer(self, rpm):
        self.ids.speedometer_sensor.text = "Speedometer: " + str(rpm)

    def speedometer_thread(self):
        while not app.stop_event.is_set():
            rpm = self.wc.read_rps(wc.SPEEDOMETER_PIN, rev_val=1) * 60
            rpm = 0
            self.update_speedometer(rpm)
            time.sleep(0.1)

    @mainthread
    def update_sensors(self, engine_state, engine_temp, engine_oil, fuel_level, water_level):
        self.ids.engine_state_sensor.text = "Engine is " + "ON" if engine_state else "OFF"
        self.ids.engine_temp_sensor.text = "Engine temp: {}Ohm".format(int(engine_temp))
        self.ids.engine_oil_sensor.text = "Engine oil: {}Ohm".format(int(engine_oil))
        self.ids.fuel_level_sensor.text = "Fuel level: {}Ohm".format(int(fuel_level))
        self.ids.water_level_sensor.text = "Water level: {}".format(water_level)

    def sensors_thread(self):
        while not app.stop_event.is_set():
            engine_state = self.wc.digital_read(wc.ENGINE_SENSOR_PIN)
            engine_temp = self.wc.read_resistance(wc.ENGINE_TEMP_PIN, 300, 3.3)
            engine_oil = self.wc.read_resistance(wc.ENGINE_OIL_PIN, 50, 3.3)
            fuel_level = self.wc.read_resistance(wc.FUEL_LEVEL_PIN, 25, 3.3)
            water_level = self.wc.digital_read_exp(wc.WATER_LEVEL_PIN)
            self.update_sensors(engine_state, engine_temp, engine_oil, fuel_level, water_level)
            time.sleep(0.5)
        

class BrushScreen(Screen):

    def __init__(self, **kwargs):
        super(BrushScreen, self).__init__(**kwargs)
        self.wc = app.wc
        # If vacuum cleaner is working or not
        self.vacuum_cleaner_state = 0
        self.brush = False
        self.water = False

        self.left_brush = False
        self.right_brush = False
        self.left_brush_in_move = False
        self.right_brush_in_move = False
        self.brush_move_time = 1 # seconds

        self.nozzle = False # Soplo
        self.nozzle_in_move = False
        self.nozzle_move_time = 1 # seconds

        threading.Thread(target=self.body_state_thread).start()
        #threading.Thread(target=self.joystick_thread).start()

    def on_brush_speed_value(self, instance, value):
        value = value / instance.max * wc.PWM_DC_RANGE
        self.wc.set_pwm_dc(wc.BRUSH_PIN, int(value))

    def update_nozzle(self):
        if self.nozzle_in_move == True:
            return
        self.nozzle_in_move = True

        to_move = False
        # Push nozzle if it's pulled and any one of the brushes is pushed
        if ((self.left_brush == True or self.right_brush == True)
                and self.nozzle == False):
            to_move = True
        # Pull nozzle if it's pushed and  both brushes are pulled
        if ((self.left_brush == False and self.right_brush == False)
                and self.nozzle == True):
            to_move = True

        if to_move == True and self.nozzle == False:
            self.wc.enable_for(wc.NOZZLE_PUSH_PIN, self.nozzle_move_time)
            self.nozzle = True
        elif to_move == True and self.nozzle == True:
            self.wc.enable_for(wc.NOZZLE_PULL_PIN, self.nozzle_move_time)
            self.nozzle = False
        self.nozzle_in_move = False

    # Move the left brush
    def on_left_brush_move_release(self):
        if self.left_brush_in_move == True:
            return
        self.left_brush_in_move = True
        if self.left_brush == False:
            self.ids.left_brush_button.background_normal = "Graphics/Brush/narr_left_pressed.tif"
            self.wc.enable_for(wc.LEFT_BRUSH_PUSH_PIN, self.brush_move_time)
            self.left_brush = True
        elif self.left_brush == True:
            self.ids.left_brush_button.background_normal = "Graphics/Brush/narr_left_normal.tif"
            self.wc.enable_for(wc.LEFT_BRUSH_PULL_PIN, self.brush_move_time)
            self.left_brush = False
        self.left_brush_in_move = False
        self.update_nozzle()


    # Move the right brush
    def on_right_brush_move_release(self):
        if self.right_brush_in_move == True:
            return
        self.right_brush_in_move = True
        if self.right_brush == False:
            self.ids.right_brush_button.background_normal = "Graphics/Brush/narr_right_pressed.tif"
            self.wc.enable_for(wc.RIGHT_BRUSH_PUSH_PIN, self.brush_move_time)
            self.right_brush = True
        elif self.right_brush == True:
            self.ids.right_brush_button.background_normal = "Graphics/Brush/narr_right_normal.tif"
            self.wc.enable_for(wc.RIGHT_BRUSH_PULL_PIN, self.brush_move_time)
            self.right_brush = False
        self.right_brush_in_move = False
        self.update_nozzle()


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
            time.sleep(0.1) # in seconds


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


    def on_stop(self):
        if self.left_brush == True:
            self.on_left_brush_move_release()
        if self.right_brush == False:
            self.on_right_brush_move_release()


class EngineScreen(Screen):

    def __init__(self, **kwargs):
        super(EngineScreen, self).__init__(**kwargs)
        self.wc = app.wc
        self.hydrapump = False
        app.motohours_f = open("/home/pi/vacuum_cleaner/motohours", "r+")
        threading.Thread(target=self.sensors_thread).start()
        threading.Thread(target=self.motohours_thread).start()

    def on_hydrapump_release(self):
        if self.hydrapump is True:
            self.hydrapump = False
            self.wc.digital_write(wc.HYDRAPUMP_PIN, 0)
            self.ids.hydrapump_button.background_normal = "Graphics/Engine/Hyd_off.tif"
        else:
            self.hydrapump = True
            self.wc.digital_write(wc.HYDRAPUMP_PIN, 1)
            self.ids.hydrapump_button.background_normal = "Graphics/Engine/Hyd_on.tif"

    @mainthread
    def update_motohours(self, motohours):
        self.ids.motohours_label.text = str(motohours)

    def motohours_thread(self):
        while not app.stop_event.is_set():
            app.motohours_f.seek(0, 0)
            motominutes = int(app.motohours_f.readline())
            motohours = int(motominutes / 60)
            self.update_motohours(motohours)
            app.motohours_f.seek(0, 0) # Seek 0 offset from start of the file
            app.motohours_f.write(str(motominutes + 1))
            time.sleep(60)

    @mainthread
    def update_sensors(self, rpm, hyd_temp, eng_temp):
        self.ids.engine_tachometer_gauge.value = rpm
        self.ids.hyd_temp_label.text = str(hyd_temp)
        self.ids.eng_temp_label.text = str(eng_temp)

    def sensors_thread(self):
        while not app.stop_event.is_set():
            rpm = self.wc.read_rps(wc.TACHOMETER_PIN, rev_val=0) * 60
            hyd_temp = self.wc.read_resistance(wc.HYD_TEMP_PIN, 300, 3.3)
            eng_temp = self.wc.read_resistance(wc.ENGINE_TEMP_PIN, 300, 3.3)
            self.update_sensors(rpm, hyd_temp, eng_temp)
            time.sleep(0.1)

    def on_engine_start_press(self):
        self.wc.digital_write(wc.ENGINE_STOP_PIN, 0)
        self.wc.digital_write(wc.ENGINE_START_PIN, 1)

    def on_engine_start_release(self):
        self.wc.digital_write(wc.ENGINE_START_PIN, 0)

    def on_engine_stop_release(self):
        self.wc.digital_write(wc.ENGINE_STOP_PIN, 1)
        time.sleep(1)
        self.wc.digital_write(wc.ENGINE_STOP_PIN, 0)

    def on_engine_speed_value(self, instance, value):
        value = value / instance.max * 2 - 1 # from -1 to 1
        print("on engine value", value)
        self.wc.engine_speed_servo(value)

    def on_stop(self):
        app.motohours_f.close()


class BodyScreen(Screen):

    def __init__(self, **kwargs):
        super(BodyScreen, self).__init__(**kwargs)
        self.wc = app.wc
        self.flasher = False
        self.lights = False
        threading.Thread(target=self.body_state_thread).start()


    def on_flasher_release(self):
        if self.flasher is True:
            self.flasher = False
            self.wc.digital_write(wc.FLASHER_PIN, 0)
            self.ids.flasher_button.background_normal = "Graphics/Body/Flasher_off.tif"
        else:
            self.flasher = True
            self.wc.digital_write(wc.FLASHER_PIN, 1)
            self.ids.flasher_button.background_normal = "Graphics/Body/Flasher_on.tif"

    def on_lights_release(self):
        if self.lights is True:
            self.lights = False
            self.wc.digital_write(wc.LIGHTS_PIN, 0)
            self.ids.lights_button.background_normal = "Graphics/Body/Lights_off.tif"
        else:
            self.lights = True
            self.wc.digital_write(wc.LIGHTS_PIN, 1)
            self.ids.lights_button.background_normal = "Graphics/Body/Lights_on.tif"



    # Movement of the body of the vehicle (up, down)
    def on_body_move_press(self, direction):
        # Button pressed
        if direction == "UP":
            self.wc.digital_write(wc.BODY_DOWN_PIN, 0)
            self.wc.digital_write(wc.BODY_UP_PIN, 1)
        elif direction == "DOWN":
            self.wc.digital_write(wc.BODY_UP_PIN, 0)
            self.wc.digital_write(wc.BODY_DOWN_PIN, 1)


    def on_body_move_release(self, direction):
        # Button released
        if direction == "UP":
            self.wc.digital_write(wc.BODY_UP_PIN, 0)
        elif direction == "DOWN":
            self.wc.digital_write(wc.BODY_DOWN_PIN, 0)


    # Get the state of the body (1 if body is up)
    def body_state(self):
        return self.wc.digital_read_from_exp(wc.BODY_STATE_PIN) ###### I added _exp ?? correct ?


    # Separate thread for updating the body state
    def body_state_thread(self):
        while not app.stop_event.is_set():
            app.body_is_up = self.body_state()
            time.sleep(0.1) # in seconds

class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super(CameraScreen, self).__init__(**kwargs)
        self.fps = 30
        self.capture = cv2.VideoCapture(0)


    def schedule_update(self):
        self.scheduled_update = Clock.schedule_interval(self.update, 1.0 / self.fps)


    def try_reopen(self):
        self.capture.release()
        self.capture = cv2.VideoCapture(0)
        return self.capture.isOpened()


    def update(self, dt):
        if not self.capture.isOpened():
            if not self.try_reopen():
                self.scheduled_update.cancel()

        ret, frame = self.capture.read()
        if ret:
            buf = cv2.flip(frame, 0).tostring()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="bgr")
            texture.blit_buffer(buf, colorfmt="bgr", bufferfmt="ubyte")
            self.ids.image.texture = texture


    def on_stop(self):
        self.capture.release()


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)

    def on_stop(self):
        pass


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
        screen_manager.add_widget(CameraScreen(name='camera'))
        screen_manager.add_widget(SettingsScreen(name='settings'))
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
