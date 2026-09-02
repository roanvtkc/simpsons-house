#!/usr/bin/env python3
"""
Simpson's House — servo calibration helper.

Jog either servo to any angle so you can find the numbers that suit YOUR
model, then put those numbers into control_garage_door() / control_door()
in mqttlistener.py.

Run:  python3 servo_calibrate.py

Commands (at the prompt):
    g            switch to the GARAGE servo   (GPIO 27)
    d            switch to the FRONT DOOR servo (GPIO 23)
    <number>     move to that angle, e.g.  90
    s A B T      sweep from A to B over T seconds, e.g.  s 0 90 2.5
    hold         keep the servo powered at its angle (it will resist being moved)
    release      stop pulsing (default — quieter, cooler, door can be nudged)
    q            quit
"""

import time
import RPi.GPIO as GPIO

GARAGE_SERVO_PIN = 27   # Garage Door Servo  (physical pin 13)
SERVO_PIN        = 23   # Front Door Servo   (physical pin 16)

# Same formula as mqttlistener.py: 0 deg -> 2% duty, 180 deg -> 12% duty at 50 Hz
DUTY_MIN = 2.0
DUTY_MAX = 12.0


def angle_to_duty(angle):
    return (angle / 180.0) * (DUTY_MAX - DUTY_MIN) + DUTY_MIN


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(GARAGE_SERVO_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(SERVO_PIN, GPIO.OUT, initial=GPIO.LOW)

pwms = {
    "garage": GPIO.PWM(GARAGE_SERVO_PIN, 50),
    "door":   GPIO.PWM(SERVO_PIN, 50),
}
for p in pwms.values():
    p.start(0)

current = "garage"
hold = False


def move(name, angle, settle=0.6):
    """Send the servo to one angle and (optionally) release the signal."""
    duty = angle_to_duty(angle)
    pwms[name].ChangeDutyCycle(duty)
    print(f"    {name:6s} -> {angle:6.1f} deg   (duty {duty:5.2f}%,"
          f" pulse ~{duty / 100 * 20:.2f} ms)")
    time.sleep(settle)
    if not hold:
        pwms[name].ChangeDutyCycle(0)


def sweep(name, start, end, seconds, steps=60):
    """Step gradually from start to end so the door moves slowly."""
    step_delay = seconds / steps
    for i in range(steps + 1):
        angle = start + (end - start) * (i / steps)
        pwms[name].ChangeDutyCycle(angle_to_duty(angle))
        time.sleep(step_delay)
    print(f"    {name:6s} swept {start} -> {end} deg over {seconds}s")
    if not hold:
        pwms[name].ChangeDutyCycle(0)


print(__doc__)
try:
    while True:
        raw = input(f"[{current}] angle/command> ").strip().lower()
        if not raw:
            continue
        if raw == "q":
            break
        elif raw == "g":
            current = "garage"
        elif raw == "d":
            current = "door"
        elif raw == "hold":
            hold = True
            print("    holding: servo stays powered (may hum, draws more current)")
        elif raw == "release":
            hold = False
            print("    releasing: signal stops after each move")
        elif raw.startswith("s "):
            try:
                _, a, b, t = raw.split()
                sweep(current, float(a), float(b), float(t))
            except ValueError:
                print("    usage: s <from> <to> <seconds>   e.g.  s 0 90 2.5")
        else:
            try:
                angle = float(raw)
            except ValueError:
                print("    not a number or a known command")
                continue
            if not 0 <= angle <= 180:
                print("    angle must be between 0 and 180")
                continue
            move(current, angle)
finally:
    for p in pwms.values():
        p.stop()
    GPIO.cleanup()
    print("\nGPIO cleaned up.")
