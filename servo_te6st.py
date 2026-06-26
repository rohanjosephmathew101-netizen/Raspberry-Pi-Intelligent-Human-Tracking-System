from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

PAN_CHANNEL = 1  # pan servo channel on PCA9685
TILT_CHANNEL = 2  # tilt servo channel on PCA9685

def smooth_sweep():
    pan_angle = 0
    tilt_angle = 5
    pan_direction = 1   # +1 means increasing angle, -1 means decreasing
    tilt_direction = 1

    try:
        while True:
            # Move pan servo smoothly full sweep
            pan_angle += 2 * pan_direction
            if pan_angle >= 180:
                pan_angle = 180
                pan_direction = -1
            elif pan_angle <= 0:
                pan_angle = 0
                pan_direction = 1
            kit.servo[PAN_CHANNEL].angle = pan_angle

            # Move tilt servo within 5-20 degrees
            tilt_angle += 1 * tilt_direction
            if tilt_angle >= 20:
                tilt_angle = 20
                tilt_direction = -1
            elif tilt_angle <= 5:
                tilt_angle = 5
                tilt_direction = 1
            kit.servo[TILT_CHANNEL].angle = tilt_angle

            print(f"Pan angle: {pan_angle}, Tilt angle: {tilt_angle}")
            time.sleep(0.05)  # delay for smooth movement

    except KeyboardInterrupt:
        print("Servo test stopped")

if __name__ == "__main__":
    smooth_sweep()
