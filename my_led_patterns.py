import board
import neopixel
import time

pixels = None

def init_led():
    global pixels
    if pixels is None:
        pixels = neopixel.NeoPixel(board.D18, 16, auto_write=True)

def blink_cross(blinks=3, speed=0.15, color=(255,0,0)):
    init_led()
    x_indices = [0, 3, 5, 6, 9, 10, 12, 15]
    for _ in range(blinks):
        pixels.fill((0,0,0))
        for i in x_indices:
            pixels[i] = color
        time.sleep(speed)
        pixels.fill((0,0,0))
        time.sleep(speed)

def blink_all(blinks=3, speed=0.15, color=(255,0,0)):
    init_led()
    for _ in range(blinks):
        pixels.fill(color)
        time.sleep(speed)
        pixels.fill((0,0,0))
        time.sleep(speed)

def face_detected_pattern():
    blink_cross(3, 0.15, (255, 0, 0))
    blink_all(3, 0.15, (255, 0, 0))
    blink_cross(3, 0.15, (255, 0, 0))
    pixels.fill((0,0,0))

def face_not_found_pattern_bg(run_event):
    init_led()
    while run_event.is_set():
        for v in range(0, 180, 10):
            if not run_event.is_set(): break
            r = int(v * 1.3)
            g = v
            b = int(v * 0.12)
            pixels.fill((r, g, b))
            time.sleep(0.028)
        for v in range(180, 0, -10):
            if not run_event.is_set(): break
            r = int(v * 1.3)
            g = v
            b = int(v * 0.12)
            pixels.fill((r, g, b))
            time.sleep(0.028)
    pixels.fill((0,0,0))
