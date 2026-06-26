import cv2
import mediapipe as mp
import time
import threading
import RPi.GPIO as GPIO
import numpy as np
from picamera2 import Picamera2
from adafruit_servokit import ServoKit
from RPLCD.i2c import CharLCD
import queue
import board
import neopixel
# --- GPIO and peripherals setup ---
SPEAKER_PIN = 21
RELAY_PIN = 26
ECHO = 13
TRIG = 19
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.HIGH)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
# --- NeoPixel Setup for LED Pattern ---
pixels = neopixel.NeoPixel(board.D18, 16, auto_write=True)
led_thread = None
stop_event = threading.Event()
x_indices = [0, 3, 5, 6, 9, 10, 12, 15]
def led_face_detected_2s():
    start = time.time()
    try:
        while time.time() - start < 2.0 and not stop_event.is_set():
            pixels.fill((0, 0, 0))
            for i in x_indices:
                pixels[i] = (255, 0, 0)
            time.sleep(0.15)
            pixels.fill((0, 0, 0))
            time.sleep(0.15)
    except Exception:
        pass
    finally:
        pixels.fill((0, 0, 0))
def start_led_pattern(pattern_func):
    global led_thread, stop_event
    if led_thread and led_thread.is_alive():
        stop_event.set()
        led_thread.join()
        stop_event.clear()
    led_thread = threading.Thread(target=pattern_func, daemon=True)
    led_thread.start()
# --- Speaker startup melody ---
pwm_lock = threading.Lock()
pwm = None
alarm_running = False
def startup_melody():
    global pwm
    with pwm_lock:
        pwm = GPIO.PWM(SPEAKER_PIN, 600)
        pwm.start(0)
        try:
            pwm.ChangeDutyCycle(50)
            for freq in range(600, 1800, 100):
                pwm.ChangeFrequency(freq)
                time.sleep(0.1)
            pwm.ChangeDutyCycle(0)
        finally:
            pwm.stop()
            pwm = None
startup_melody()
# --- LCD Setup ---
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=20, rows=4, charmap='A02', auto_linebreaks=True)
# Ultrasonic sensor
distance = None
distance_lock = threading.Lock()
running = True
def measure_distance(timeout=1):
    GPIO.output(TRIG, False)
    time.sleep(0.05)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    timeout_start = time.time()
    while GPIO.input(ECHO) == 0:
        if time.time() - timeout_start > timeout:
            return None
    start_time = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time() - timeout_start > timeout:
            return None
    stop_time = time.time()
    duration = stop_time - start_time
    dist = (duration * 34300) / 2
    return round(dist, 2)
def ultrasonic_sensor_thread():
    global distance
    while running:
        dist = measure_distance()
        if dist is not None:
            dist_rounded = round(dist / 5) * 5
            with distance_lock:
                distance = dist_rounded
        time.sleep(0.2)
ultra_thread = threading.Thread(target=ultrasonic_sensor_thread, daemon=True)
ultra_thread.start()
# Servos setup
kit = ServoKit(channels=16, address=0x40)
PAN_CHANNEL = 1
TILT_CHANNEL = 2
PUSH_CHANNEL = 7
INITIAL_PAN_ANGLE = 160
INITIAL_TILT_ANGLE = 0
PUSH_SERVO_START = 0
kit.servo[PAN_CHANNEL].angle = INITIAL_PAN_ANGLE
kit.servo[TILT_CHANNEL].angle = INITIAL_TILT_ANGLE
kit.servo[PUSH_CHANNEL].angle = PUSH_SERVO_START
GPIO.output(RELAY_PIN, GPIO.HIGH)
shooting = False
pause_tracking = False
shoot_lock = threading.Lock()
shoot_permission_queue = queue.Queue()
def cyberpunk_lockon_alarm():
    global pwm, alarm_running
    with pwm_lock:
        if alarm_running or shooting:
            return
        alarm_running = True
        try:
            if pwm is None:
                pwm = GPIO.PWM(SPEAKER_PIN, 800)
            pwm.start(50)
            for freq in range(600, 1800, 100):
                pwm.ChangeFrequency(freq)
                time.sleep(0.03)
            for _ in range(6):
                pwm.ChangeFrequency(1200)
                time.sleep(0.04)
                pwm.ChangeFrequency(1800)
                time.sleep(0.04)
            for freq in range(1600, 300, -130):
                pwm.ChangeFrequency(freq)
                time.sleep(0.01)
            pwm.stop()
        finally:
            alarm_running = False
def play_alarm_async():
    threading.Thread(target=cyberpunk_lockon_alarm, daemon=True).start()
def shoot_sequence():
    global shooting, pause_tracking, alarm_running
    with shoot_lock:
        if shooting:
            return
        shooting = True
        pause_tracking = True
        alarm_running = True  # Suppress alarm during shooting
        GPIO.output(RELAY_PIN, GPIO.LOW)
        time.sleep(0.5)
        kit.servo[PUSH_CHANNEL].angle = 180
        time.sleep(2)
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        kit.servo[PUSH_CHANNEL].angle = PUSH_SERVO_START
        shooting = False
        pause_tracking = False
        alarm_running = False
def prompt_shoot_permission():
    while True:
        event_time = shoot_permission_queue.get()
        if event_time is None:
            break
        answer = input("Face detected. Shoot? (y/n): ").strip().lower()
        shoot_permission_queue.task_done()
        if answer == "y" and not shooting:
            threading.Thread(target=shoot_sequence, daemon=True).start()
threading.Thread(target=prompt_shoot_permission, daemon=True).start()
# Face detection setup
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.55)
USE_PICAMERA = True
try:
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (320, 240), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    time.sleep(0.5)
except:
    USE_PICAMERA = False
cap = cv2.VideoCapture(0) if not USE_PICAMERA else None
if cap and not cap.isOpened():
    raise RuntimeError("Cannot open webcam")
DEADBAND_X = 50
DEADBAND_Y = 25
ALPHA = 0.35
MAX_PAN_DELTA = 3.0
MAX_TILT_DELTA = 1.5
MIN_MOVE_DEG = 1.0
UPDATE_INTERVAL = 0.05
PAN_GAIN = 0.03
TILT_GAIN = 0.025
PAN_MIN, PAN_MAX = 0, 180
TILT_MIN, TILT_MAX = 5, 25
pan_angle = INITIAL_PAN_ANGLE
tilt_angle = INITIAL_TILT_ANGLE
prev_dx, prev_dy = 0.0, 0.0
last_update = time.time()
face_cycle = None
try:
    lcd.clear()
    lcd.write_string("BY: ROHAN JOSEPH")
    time.sleep(2)
    lcd.clear()
    lcd.write_string("AWAITING ENEMY")
    while True:
        if USE_PICAMERA:
            frame = picam2.capture_array()
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            ret, frame = cap.read()
            if not ret:
                break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detector.process(frame_rgb)
        h, w = frame.shape[:2]
        if results.detections:
            det = results.detections[0]
            rb = det.location_data.relative_bounding_box
            cx = int(rb.xmin * w + rb.width * w / 2)
            cy = int(rb.ymin * h + rb.height * h / 2)
            size = 90
            tri = [(cx, cy+size), (cx-size, cy-size), (cx+size, cy-size)]
            cv2.polylines(frame, [np.array(tri)], True, (0,0,255), 3)
            dx_raw = cx - w // 2
            dy_raw = cy - h // 2
            sm_dx = ALPHA * dx_raw + (1 - ALPHA) * prev_dx
            sm_dy = ALPHA * dy_raw + (1 - ALPHA) * prev_dy
            prev_dx, prev_dy = sm_dx, sm_dy
            now = time.time()
            if now - last_update >= UPDATE_INTERVAL and not pause_tracking:
                if abs(sm_dx) > DEADBAND_X:
                    desired_pan = pan_angle - sm_dx * PAN_GAIN
                    delta_pan = max(-MAX_PAN_DELTA, min(MAX_PAN_DELTA, desired_pan - pan_angle))
                    new_pan = pan_angle + delta_pan
                    new_pan = max(PAN_MIN, min(PAN_MAX, new_pan))
                    if abs(new_pan - pan_angle) > MIN_MOVE_DEG:
                        pan_angle = new_pan
                        kit.servo[PAN_CHANNEL].angle = pan_angle
                if abs(sm_dy) > DEADBAND_Y:
                    desired_tilt = tilt_angle - sm_dy * TILT_GAIN
                    delta_tilt = max(-MAX_TILT_DELTA, min(MAX_TILT_DELTA, desired_tilt - tilt_angle))
                    new_tilt = tilt_angle + delta_tilt
                    new_tilt = max(TILT_MIN, min(TILT_MAX, new_tilt))
                    if abs(new_tilt - tilt_angle) > MIN_MOVE_DEG:
                        tilt_angle = new_tilt
                        kit.servo[TILT_CHANNEL].angle = tilt_angle
                last_update = now
            with distance_lock:
                dist_val = distance
            lcd.clear()
            if dist_val is not None:
                lcd.write_string(f"Distance: {int(dist_val)} cm")
            else:
                lcd.write_string("Distance: N/A")
            if face_cycle is None:
                # LED blinks for 2s when a new face appears
                start_led_pattern(led_face_detected_2s)
                face_cycle = {'since': now}
                play_alarm_async()
                shoot_permission_queue.put(now)
        else:
            prev_dx, prev_dy = 0.0, 0.0
            face_cycle = None
            lcd.clear()
            lcd.write_string("WAITING FOR ENEMY")
        cv2.imshow("Face Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    running = False
    shoot_permission_queue.put(None)
    stop_event.set()
    pixels.fill((0, 0, 0))
    if led_thread and led_thread.is_alive():
        led_thread.join()
    if USE_PICAMERA and picam2 is not None:
        try:
            picam2.close()
        except:
            pass
    if cap and not USE_PICAMERA:
        try:
            cap.release()
        except:
            pass
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.output(SPEAKER_PIN, GPIO.LOW)
    GPIO.cleanup()
    lcd.clear()
    cv2.destroyAllWindows()
