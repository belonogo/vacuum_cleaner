from functools import partial
from subprocess import call
import threading
from threading import Thread
import time
import os
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

IGNITION_STATUS = 0
FUEL_CURRENT_LEVEL, FUEL_CRITICAL_LEVEL = 0, 100
ENGINE_CURRENT_TEMP, ENGINE_CRITICAL_TEMP = 0, 120
WATER_CURRENT_LEVEL, WATER_CRITICAL_LEVEL = 0, 120
BATTERY_CURRENT_LEVEL, BATTERY_CRTICAL_LEVEL = 0, 100


class BaseScreen(Screen):

    def __init__(self, **kwargs):
        super(BaseScreen, self).__init__(**kwargs)
        self.wc = app.wc
        self.POWER_STATUS = 1
        self.TICK_COUNTER = 30
        threading.Thread(target=self.update_icon_thread).start()
        threading.Thread(target=self.check_power_thread).start()
        threading.Thread(target=self.update_fuel_status).start()
        threading.Thread(target=self.timer).start()
        threading.Thread(target=self.shutdown).start()
        self.ids.base_sm.current = 'brush'

    def on_stop(self):
        app.wc.stop_all()

    @mainthread
    def update_icon(self):
        pass

    def update_icon_thread(self):
        while not app.stop_event.is_set():

            if float(FUEL_CURRENT_LEVEL)/float(FUEL_CRITICAL_LEVEL) <= 0.15:
                self.ids.indicator_gasoline.opacity = 1.0
            elif float(FUEL_CURRENT_LEVEL)/float(FUEL_CRITICAL_LEVEL) > 0.15:
                self.ids.indicator_gasoline.opacity = 0.0

            if ENGINE_CURRENT_TEMP/ENGINE_CRITICAL_TEMP > 0.85:
                self.ids.indicator_overheat.opacity = 1.0
            else:
                self.ids.indicator_overheat.opacity = 0.0

            if WATER_CURRENT_LEVEL/WATER_CRITICAL_LEVEL <= 0.15:
                self.ids.indicator_water.opacity = 1.0
            else:
                self.ids.indicator_water.opacity = 0.0

            if self.POWER_STATUS == 1:
                self.ids.indicator_ignition.opacity = 1.0
            else:
                self.ids.indicator_ignition.opacity = 0.0

            self.update_icon()
            time.sleep(0.5)

    def check_power_thread(self):
        while not app.stop_event.is_set():
            current_power_level = self.wc.analog_read(wc.POWER_CHECK_PIN)
            power_state = 1
            if current_power_level > 0.4:
                power_state = 1
                self.POWER_STATUS = power_state
                self.TICK_COUNTER = 30
            else:
                power_state = 0
                self.POWER_STATUS = power_state
            global IGNITION_STATUS
            IGNITION_STATUS = power_state

            self.update_icon()
            time.sleep(0.1)

    def shutdown(self):
        while not app.stop_event.is_set():
            if self.TICK_COUNTER == 0:
                os.system("shutdown now -h")
                self.update_icon()
                time.sleep(0.1)

    def timer(self):
        while not app.stop_event.is_set():
            self.ids.tick_counter.text = "{}".format(int(self.TICK_COUNTER))
            self.TICK_COUNTER -= 1;
            time.sleep(1)
            self.update_icon()


    def update_fuel_status(self):
        while not app.stop_event.is_set():
            self.ids.gasoline_text.text = "{}%".format(int(FUEL_CURRENT_LEVEL))
            self.update_icon()
            time.sleep(0.1)


class SensorScreen(Screen):

    def __init__(self, **kwargs):
        super(SensorScreen, self).__init__(**kwargs)
        self.wc = app.wc
        threading.Thread(target=self.speedometer_thread).start()
        threading.Thread(target=self.sensors_thread).start()

    @mainthread
    def update_speedometer(self, rpm):
        #self.ids.speedometer_sensor.text = "Speedometer: " + str(rpm)
        temp = 1

    def speedometer_thread(self):
        while not app.stop_event.is_set():
            rpm = self.wc.read_rps(wc.SPEEDOMETER_PIN, rev_val=1) * 60
            rpm = 0
            self.update_speedometer(rpm)
            time.sleep(0.1)

    @mainthread
    def update_sensors(self, engine_state, engine_temp, hyd_temp, fuel_level, water_level):

        global FUEL_CURRENT_LEVEL
        FUEL_CURRENT_LEVEL = int(self.convert_ohm_to_temp(0, 100, 10, 1000, fuel_level))
        self.ids.fuel_level_sensor.text = "Уровень топлива: {} %".format(int(FUEL_CURRENT_LEVEL))

        global ENGINE_CURRENT_TEMP
        ENGINE_CURRENT_TEMP = int(self.convert_ohm_to_temp(30, 120, 100, 1000, engine_temp))
        self.ids.engine_temp_sensor.text = "Температура ОЖ: {} С°".format(int(ENGINE_CURRENT_TEMP))

        global WATER_CURRENT_LEVEL
        WATER_CURRENT_LEVEL = int(self.convert_ohm_to_temp(30, 120, 100, 1000, hyd_temp))
        self.ids.hyd_temp_sensor.text = "Температура ГЖ: {} С°".format(int(WATER_CURRENT_LEVEL))

        global BATTERY_CURRENT_LEVEL
        BATTERY_CURRENT_LEVEL = 100

        IGNITION_STATUS_STRING = "выключен"
        if IGNITION_STATUS == 1:
            IGNITION_STATUS_STRING = "включен"
        else:
            IGNITION_STATUS_STRING = "выключен"
        self.ids.eng_status_sensor.text = "Статус двигателя: {}".format(IGNITION_STATUS_STRING)

    def convert_ohm_to_temp(self, t_min, t_max, o_min, o_max, o_value):
        t_count = t_max - t_min + 1
        o_count = o_max - o_min + 1
        to_coeff = o_count / t_count
        o_k = o_value - o_min + 1
        t_k = round(o_k / to_coeff)
        t_value = t_min + t_k - 1
        if t_k < 1:
            t_value = t_min
        return t_value

    def sensors_thread(self):
        while not app.stop_event.is_set():
            engine_state = self.wc.digital_read(wc.ENGINE_SENSOR_PIN)

            fuel_level = self.wc.read_resistance(wc.FUEL_LEVEL_PIN, 25, 3.3)
            engine_temp = self.wc.read_resistance(wc.ENGINE_TEMP_PIN, 980, 3.3)
            hyd_temp = self.wc.read_resistance(wc.HYD_TEMP_PIN, 50, 3.3)

            water_level = self.wc.digital_read_exp(wc.WATER_LEVEL_PIN)
            self.update_sensors(engine_state, engine_temp, hyd_temp, fuel_level, water_level)
            time.sleep(0.5)
        

class BrushScreen(Screen):

    def __init__(self, **kwargs):
        super(BrushScreen, self).__init__(**kwargs)
        self.wc = app.wc
        # If vacuum cleaner is working or not
        self.vacuum_cleaner_state = 0
        self.l_brush = False
        self.r_brush = False
        self.water = False
        threading.Thread(target=self.body_state_thread).start()
        threading.Thread(target=self.joystick_thread).start()

    def on_brush_speed_value(self, instance, value):
        value = value / instance.max * wc.PWM_DC_RANGE
        self.wc.set_pwm_dc(wc.BRUSH_PIN, int(value))

    # Movement of the brushes (up, down, pull apart, bring closer)
    def on_brush_move_press(self, direction):
        # When the button is pressed
        if direction == "L_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.BRUSH_LEFT_UP_SPI_PIN)
        elif direction == "L_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.BRUSH_LEFT_DOWN_SPI_PIN)
        elif direction == "R_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.BRUSH_RIGHT_UP_SPI_PIN)
        elif direction == "R_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.BRUSH_RIGHT_DOWN_SPI_PIN)
        elif direction == "N_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.NOZZLE_UP_SPI_PIN)
        elif direction == "N_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.NOZZLE_DOWN_SPI_PIN)

    def on_brush_move_release(self, direction):
        # When the button is released
        if direction == "L_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
        elif direction == "L_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)
        elif direction == "R_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
        elif direction == "R_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)
        elif direction == "N_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
        elif direction == "N_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)

    # Switch vacuum cleaner state if possible
    def on_vacuum_cleaner_button_release(self):
        if self.vacuum_cleaner_state == 0 and app.body_is_up == 0:
            # We can only enable it
            # if the vacuum cleaner is disabled and the body is down.
            self.wc.digital_write(wc.VACUUM_CLEANER_SWITCH_PIN, 1)
            self.vacuum_cleaner_state = 1
            self.ids.vacuum_cleaner_button.background_normal = "Graphics/Brush/Vacuum_button_pressed.tif"
            for i in range(1025):
                value = i
                self.wc.set_pwm_dc(wc.BRUSH_PIN, int(value))
                time.sleep(0.00976)


        elif self.vacuum_cleaner_state == 1:
            # If the vacuum cleaner is enabled,
            # then we can disable it regardless of the body state.
            self.wc.digital_write(wc.VACUUM_CLEANER_SWITCH_PIN, 0)
            self.vacuum_cleaner_state = 0
            self.ids.vacuum_cleaner_button.background_normal = "Graphics/Brush/Vacuum_button_normal.tif"
            self.wc.set_pwm_dc(wc.BRUSH_PIN, int(0))

    # Separate thread for disabling vacuum cleaner on body_is_up
    def body_state_thread(self):
        while not app.stop_event.is_set():
            if app.body_is_up and self.vacuum_cleaner_state:
                # if the body is up, the vacuum cleaner must be disabled.
                self.on_vacuum_cleaner_switch_release()
            time.sleep(0.1) # in seconds

    def joystick_thread(self):
        pins = [wc.JOYSTICK_PIN, wc.JOYSTICK_PIN, wc.JOYSTICK_PIN, wc.JOYSTICK_PIN, wc.JOYSTICK_PIN, wc.JOYSTICK_PIN]
        dirs = ["L_UP", "L_DOWN", "R_UP", "R_DOWN", "N_UP", "N_DOWN"]
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

    def on_brush_l_button_release(self):
        print("Brush button pressed!")
        if self.l_brush is True:
            self.l_brush = False
            self.wc.digital_write(wc.BRUSH_L_SWITCH_PIN, 0)
            print("brush_l written 0")
            self.ids.brush_button_l.background_normal = "Graphics/Brush/Brush_l_button_normal.tif"
        else:
            self.l_brush = True
            self.wc.digital_write(wc.BRUSH_L_SWITCH_PIN, 1)
            print("brush_l written 1")
            self.ids.brush_button_l.background_normal = "Graphics/Brush/Brush_l_button_pressed.tif"

    def on_brush_r_button_release(self):
        print("Brush button pressed!")
        if self.r_brush is True:
            self.r_brush = False
            self.wc.digital_write(wc.BRUSH_R_SWITCH_PIN, 0)
            print("brush_r written 0")
            self.ids.brush_button_r.background_normal = "Graphics/Brush/Brush_r_button_normal.tif"
        else:
            self.r_brush = True
            self.wc.digital_write(wc.BRUSH_R_SWITCH_PIN, 1)
            print("brush_r written 1")
            self.ids.brush_button_r.background_normal = "Graphics/Brush/Brush_r_button_pressed.tif"

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
            self.wc.digital_write_exp(wc.HYDRAPUMP_PIN, 0)
            self.ids.hydrapump_button.background_normal = "Graphics/Engine/Hyd_off.tif"
        else:
            self.hydrapump = True
            self.wc.digital_write_exp(wc.HYDRAPUMP_PIN, 1)
            self.ids.hydrapump_button.background_normal = "Graphics/Engine/Hyd_on.tif"

    @mainthread
    def update_motohours(self, motohours):
        pass
        #self.ids.motohours_label.text = str(motohours)

    def motohours_thread(self):
        while not app.stop_event.is_set():
            app.motohours_f.seek(0, 0)
            motominutes = int(app.motohours_f.readline())
            motohours = int(motominutes / 60)
            self.update_motohours(motohours)
            app.motohours_f.seek(0, 0)  # Seek 0 offset from start of the file
            app.motohours_f.write(str(motominutes + 1))
            time.sleep(60)

    @mainthread
    def update_sensors(self, rpm, hyd_temp, eng_temp):
        self.ids.engine_tachometer_gauge.value = rpm
        eng_temp = int(self.convert_ohm_to_temp(30, 120, 100, 1000, eng_temp))
        hyd_temp = int(self.convert_ohm_to_temp(30, 120, 100, 1000, hyd_temp))
        self.ids.hyd_temp_text.text = "{}".format(int(hyd_temp))
        self.ids.eng_temp_text.text = "{}".format(int(eng_temp))

    def sensors_thread(self):
        while not app.stop_event.is_set():
            rpm = self.wc.read_rps(wc.TACHOMETER_PIN, rev_val=0) * 60
            engine_temp = self.wc.read_resistance(wc.ENGINE_TEMP_PIN, 980, 3.3)
            hyd_temp = self.wc.read_resistance(wc.HYD_TEMP_PIN, 50, 3.3)
            self.update_sensors(rpm, hyd_temp, engine_temp)
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
        value = value / instance.max * 2 - 1  # from -1 to 1
        print("on engine value", value)
        self.wc.engine_speed_servo(value)

    def on_stop(self):
        app.motohours_f.close()

    def convert_ohm_to_temp(self, t_min, t_max, o_min, o_max, o_value):
        t_count = t_max - t_min + 1
        o_count = o_max - o_min + 1
        to_coeff = o_count / t_count
        o_k = o_value - o_min + 1
        t_k = round(o_k / to_coeff)
        t_value = t_min + t_k - 1
        if t_k < 1:
            t_value = t_min
        return t_value


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
        if direction == "B_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.BODY_UP_SPI_PIN)
        elif direction == "B_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)
            self.wc.spi_write(wc.BODY_DOWN_SPI_PIN)

    def on_body_move_release(self, direction):
        # Button released
        if direction == "B_UP":
            self.wc.spi_write(wc.SPI_OFF_PIN)
        elif direction == "B_DOWN":
            self.wc.spi_write(wc.SPI_OFF_PIN)

    # Get the state of the body (1 if body is up)
    def body_state(self):
        return self.wc.digital_read(wc.BODY_STATE_PIN)

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


class PasswordScreen(Screen):

    def __init__(self, **kwargs):
        super(PasswordScreen, self).__init__(**kwargs)

    def on_stop(self):
        pass

    def add_in_line(self, input):
        self.ids.input_password.text += input

    def clear_line(self):
        self.ids.input_password.text = ""

    def read_password(self):
        password = self.ids.input_password.text
        if password == '2022':
            self.manager.current = 'settings'
        self.clear_line()

    def back_to_main_screen(self):
        self.manager.current = 'base'


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
        screen_manager.add_widget(PasswordScreen(name='password'))
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
