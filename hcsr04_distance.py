import RPi.GPIO as GPIO
import time

# Define GPIO pins
ECHO = 13  # BCM GPIO 13, Physical Pin 33
TRIG = 19  # BCM GPIO 19, Physical Pin 35

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance(timeout=1):
    # Ensure trigger is low
    GPIO.output(TRIG, False)
    time.sleep(0.05)

    # Send 10us pulse to trigger
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time = time.time()
    timeout_start = start_time

    # Wait for echo to go high or timeout
    while GPIO.input(ECHO) == 0:
        start_time = time.time()
        if start_time - timeout_start > timeout:
            print("Timeout waiting for ECHO to go HIGH")
            return None

    stop_time = time.time()
    timeout_start = stop_time

    # Wait for echo to go low or timeout
    while GPIO.input(ECHO) == 1:
        stop_time = time.time()
        if stop_time - timeout_start > timeout:
            print("Timeout waiting for ECHO to go LOW")
            return None

    duration = stop_time - start_time

    # Calculate distance (cm)
    distance = (duration * 34300) / 2
    distance = round(distance, 2)

    return distance

try:
    while True:
        dist = measure_distance()
        if dist is not None:
            print(f"Distance: {dist} cm")
        else:
            print("Failed to get valid distance measurement")
        time.sleep(1)
except KeyboardInterrupt:
    print("Measurement stopped by user")
finally:
    GPIO.cleanup()
