import RPi.GPIO as GPIO
import time

TRIG = 19  # Pin 35
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)

GPIO.output(TRIG, True)
time.sleep(0.00001)  #  pulse
GPIO.output(TRIG, False)

GPIO.cleanup()
