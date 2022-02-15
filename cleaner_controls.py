import wiringpi as wp
import RPi.GPIO as GPIO


# BCM numbering (WiringPi & Troyka Cap physical numbering)
BRUSH_PIN = 18 #(1~)

# WiringPi Numbering
BRUSH_UP_PIN = 6
BRUSH_DOWN_PIN = 5
# APART for pushing the brushes apart
BRUSH_APART_PIN = 3
# CLOSE for bringing the brushes closer
BRUSH_CLOSE_PIN = 4
BODY_UP_PIN = 2
BODY_DOWN_PIN = 0

# Magic numbers
PWM_FREQUENCY = 50
LOW = 0
PWM_DC_RANGE = 100


class CleanerControls:
    def __init__(self):
        # setup RPi.GPIO
        # set BCM pin numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BRUSH_PIN, GPIO.OUT)

        self.brush_pwm = GPIO.PWM(BRUSH_PIN, PWM_FREQUENCY)
        self.brush_pwm.start(LOW)

        # setup WiringPi
        wp.wiringPiSetup()
        wp.pinMode(BRUSH_UP_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_DOWN_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_APART_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BRUSH_CLOSE_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BODY_UP_PIN, wp.GPIO.OUTPUT)
        wp.pinMode(BODY_DOWN_PIN, wp.GPIO.OUTPUT)


    def digitalWrite(self, pin, value):
        wp.digitalWrite(pin, value)


    def set_pwm_dc(self, pwm_instance, value):
        pwm_instance.ChangeDutyCycle(value)


    def stop_all(self):
        self.brush_pwm.stop()
        GPIO.cleanup()

        wp.digitalWrite(BRUSH_UP_PIN, LOW)
        wp.digitalWrite(BRUSH_DOWN_PIN, LOW)
        wp.digitalWrite(BRUSH_APART_PIN, LOW)
        wp.digitalWrite(BRUSH_CLOSE_PIN, LOW)
        wp.digitalWrite(BODY_UP_PIN, LOW)
        wp.digitalWrite(BODY_DOWN_PIN, LOW)

# wiringPi doesn't work
#def setup():
#    wp.wiringPiSetup()
#    # pwmRange is 1024 by default; change to 12
#    wp.pwmSetRange(12)
#    wp.pinMode(BRUSH_PIN, wp.GPIO.PWM_OUTPUT)

#def set_brush_speed(value):
#    # Speed of the brush rotation
#    wp.pwmWrite(BRUSH_PIN, value)
