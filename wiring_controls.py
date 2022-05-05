import wiringpi as wp
import gpioexp
import time
from gpiozero import AngularServo
import spidev


# SPI settings and pins
SPI_BUS = 0
SPI_SS = 1
SPI_CLOCK = 1000000
SPI_OFF_PIN = 0
SPI_POWER_PIN = 6
BRUSH_LEFT_UP_SPI_PIN = 0x01
BRUSH_LEFT_DOWN_SPI_PIN = 0x02
BRUSH_RIGHT_UP_SPI_PIN = 0x04
BRUSH_RIGHT_DOWN_SPI_PIN = 0x08
NOZZLE_UP_SPI_PIN = 0x10
NOZZLE_DOWN_SPI_PIN = 0x20
BODY_UP_SPI_PIN = 0x40
BODY_DOWN_SPI_PIN = 0x80

# GPIO pins
SPEEDOMETER_PIN = 0
BRUSH_PIN = 1

VACUUM_CLEANER_SWITCH_PIN = 3
WATER_SWITCH_PIN = 4
BODY_STATE_PIN = 5
ENGINE_START_PIN = 7
ENGINE_SPEED_PIN = 15
ENGINE_STOP_PIN = 21
ENGINE_SENSOR_PIN = 22
LIGHTS_PIN = 25
TACHOMETER_PIN = 26
FLASHER_PIN = 27
BRUSH_L_SWITCH_PIN = 28
BRUSH_R_SWITCH_PIN = 29
# Joystick management

"""
JOYSTICK_UP_PIN = 16
JOYSTICK_DOWN_PIN = 24
JOYSTICK_L_BRUSH_PIN = 27
JOYSTICK_R_BRUSH_PIN = 23
JOYSTICK_NOZZLE_PIN = 28
JOYSTICK_ALL_PIN = 29
"""

# Expander (analog) pins
WATER_LEVEL_PIN = 0
FUEL_LEVEL_PIN = 1
ENGINE_OIL_PIN = 2
ENGINE_TEMP_PIN = 3
POWER_CHECK_PIN = 5
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
        wp.pinMode(VACUUM_CLEANER_SWITCH_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(ENGINE_START_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(ENGINE_STOP_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_L_SWITCH_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_R_SWITCH_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(WATER_SWITCH_PIN, wp.GPIO.OUTPUT)

        # HARD PWM wiringPi
        wp.pwmSetClock(PWM_CLOCK)
        wp.pwmSetRange(PWM_DC_RANGE)
        wp.pinMode(BRUSH_PIN, wp.GPIO.PWM_OUTPUT)
        wp.pinMode(LIGHTS_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(FLASHER_PIN, wp.GPIO.OUTPUT)
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
        wp.pinMode(POWER_CHECK_PIN, wp.GPIO.INPUT)
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

    def read_resistance(self, pin, R2, Vin):
        raw_signal = self.analog_read(pin)
        Vout = raw_signal
        R1 = ((Vin * R2) / Vout) - R2
        return R1

    def digital_read_exp(self, pin):
        val = self.analog_read(pin)
        return 1 if val > 0.5 else 0

    def digital_write_exp(self, pin, val):
        val = 1 if val >= 0.5 else 0
        self.exp.analogWrite(pin, val)

    def engine_speed_servo(self, val):
        self.engine_servo.value = val

    def stop_all(self):
        self.digital_write(LIGHTS_PIN, LOW)
        self.digital_write(FLASHER_PIN, LOW)
        self.digital_write(SPI_POWER_PIN, LOW)
        self.digital_write(VACUUM_CLEANER_SWITCH_PIN, LOW)
        self.digital_write(ENGINE_START_PIN, LOW)
        self.digital_write(ENGINE_STOP_PIN, LOW)
        self.digital_write(BRUSH_L_SWITCH_PIN, LOW)
        self.digital_write(BRUSH_R_SWITCH_PIN, LOW)
        self.digital_write(WATER_SWITCH_PIN, LOW)
        self.set_pwm_dc(BRUSH_PIN, LOW)

    def spi_write(self, pin):
        spi = spidev.SpiDev(SPI_BUS, SPI_SS)
        spi.max_speed_hz = SPI_CLOCK
        send = [0, pin]
        spi.xfer(send)
        spi.close()