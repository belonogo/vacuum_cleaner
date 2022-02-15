import wiringpi as wp
import gpioexp
import time
from gpiozero import AngularServo


# WiringPi Numbering
BRUSH_UP_PIN = 6
BRUSH_DOWN_PIN = 5
BRUSH_APART_PIN = 3 # APART for pushing the brushes apart
BRUSH_CLOSE_PIN = 4 # CLOSE for bringing the brushes closer
BRUSH_PIN = 1
BODY_UP_PIN = 24
BODY_DOWN_PIN = 0
VACUUM_CLEANER_SWITCH_PIN = 7

# !!! Collision with JOYSTICK pins!
BRUSH_SWITCH_PIN = 2
WATER_SWITCH_PIN = 27

# !!! not wiringPi numbering
ENGINE_SPEED_PIN = 15 # wiringPi 16 / RX
# !!! end of not wiringPi numbering

BODY_STATE_PIN = 10
#PIN THAT IS ALWAYS HIGH = 11
ENGINE_START_PIN = 21
ENGINE_STOP_PIN = 22
TACHOMETER_PIN = 26
SPEEDOMETER_PIN = 23

JOYSTICK_UP_PIN = 24
JOYSTICK_DOWN_PIN = 27
JOYSTICK_LEFT_PIN = 25
JOYSTICK_RIGHT_PIN = 28
ENGINE_SENSOR_PIN = 29

# Expander (analog) pins
ENGINE_TEMP_PIN = 3
ENGINE_OIL_PIN = 2
FUEL_LEVEL_PIN = 1
WATER_LEVEL_PIN = 0

FLASHER_PIN = 4
LIGHTS_PIN = 5
HYDRAPUMP_PIN = 6
HYD_TEMP_PIN = 7

# Magic numbers
LOW = 0
HIGH = 1
PWM_CLOCK = 192
PWM_DC_RANGE = 1024


class WiringControls:
    def __init__(self):
        # setup WiringPi
        wp.wiringPiSetup()
        self.exp = gpioexp.gpioexp()
        wp.pinMode(BRUSH_UP_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_DOWN_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_APART_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_CLOSE_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BODY_UP_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BODY_DOWN_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(VACUUM_CLEANER_SWITCH_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(ENGINE_START_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(ENGINE_STOP_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_SWITCH_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(WATER_SWITCH_PIN, wp.GPIO.OUTPUT)

        # HARD PWM wiringPi
        wp.pwmSetClock(PWM_CLOCK)
        wp.pwmSetRange(PWM_DC_RANGE)
        wp.pinMode(BRUSH_PIN, wp.GPIO.PWM_OUTPUT)
        # mark-space mode
        wp.pwmSetMode(wp.GPIO.PWM_MODE_MS)

        # wiringPi BODY_STATE input with pull down
        wp.pinMode(BODY_STATE_PIN, wp.GPIO.INPUT)
        wp.pullUpDnControl(BODY_STATE_PIN, wp.GPIO.PUD_DOWN)
        wp.pinMode(TACHOMETER_PIN, wp.GPIO.INPUT)
        wp.pinMode(SPEEDOMETER_PIN, wp.GPIO.INPUT)
        #wp.pinMode(JOYSTICK_UP_PIN, wp.GPIO.INPUT) # !!! Commented!
        #wp.pinMode(JOYSTICK_DOWN_PIN, wp.GPIO.INPUT) # !!!
        #wp.pinMode(JOYSTICK_LEFT_PIN, wp.GPIO.INPUT) # !!!
        #wp.pinMode(JOYSTICK_RIGHT_PIN, wp.GPIO.INPUT) # !!!
        wp.pinMode(ENGINE_SENSOR_PIN, wp.GPIO.INPUT)

        self.engine_servo = AngularServo(ENGINE_SPEED_PIN, min_pulse_width = 0.5/1000, max_pulse_width = 2.1/1000)


    def digital_write(self, pin, value):
        wp.digitalWrite(pin, value)


    def digital_read(self, pin):
        return wp.digitalRead(pin) 

    def set_pwm_dc(self, pin, value):
        wp.pwmWrite(pin, value)


    # For tachometer and speedometer, based on Hall effect
    def read_rps(self, pin, rev_val):
        if rev_val != 0 and rev_val != 1:
            raise Exception('invalid rev val {}' % rev_val)
        cnt = 0
        flag = False
        start = time.time()
        while time.time() - start < 1:
            val = self.digital_read(pin)
            if val == 1 - rev_val:
                flag = True
            elif val == rev_val and flag:
                flag = False
                cnt = cnt + 1
        return cnt

    def analog_read(self, pin):
        return self.exp.analogRead(pin)

    def read_resistance(self, pin, R1, Vin):
        raw_signal = self.analog_read(pin)
        Vout = raw_signal * Vin
        R2 = R1 * (Vin / Vout - 1)
        return R2

    def digital_read_exp(self, pin):
        val = self.analog_read(pin)
        return 1 if val > 0.5 else 0

    def digital_write_exp(self, pin, val):
        val = 1 if val >= 0.5 else 0
        self.exp.analogWrite(pin, val)

    def engine_speed_servo(self, val):
        self.engine_servo.value = val
        

    def stop_all(self):
        self.digital_write(BRUSH_UP_PIN, LOW)
        self.digital_write(BRUSH_DOWN_PIN, LOW)
        self.digital_write(BRUSH_APART_PIN, LOW)
        self.digital_write(BRUSH_CLOSE_PIN, LOW)
        self.digital_write(BODY_UP_PIN, LOW)
        self.digital_write(BODY_DOWN_PIN, LOW)
        self.digital_write(VACUUM_CLEANER_SWITCH_PIN, LOW)
        self.digital_write(ENGINE_START_PIN, LOW)
        self.digital_write(ENGINE_STOP_PIN, LOW)
        self.digital_write(BRUSH_SWITCH_PIN, LOW)
        self.digital_write(WATER_SWITCH_PIN, LOW)
        self.set_pwm_dc(BRUSH_PIN, LOW)


