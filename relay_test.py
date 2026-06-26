import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)

try:
    while True:
        GPIO.output(26, GPIO.LOW)  # Relay ON (check logic)
        print("Relay ON")
        time.sleep(1)
        GPIO.output(26, GPIO.HIGH)  # Relay OFF
        print("Relay OFF")
        time.sleep(1)
except KeyboardInterrupt:
    pass

GPIO.cleanup()
