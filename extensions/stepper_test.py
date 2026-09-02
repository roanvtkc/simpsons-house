#!/usr/bin/env python3
"""
Simpson's House — Stepper Motor Test (EXTENSION)

Drives a 28BYJ-48 stepper motor through a ULN2003 driver board, one
revolution forward and one back.

This is EXTENSION hardware. The garage door in the standard build uses an
SG90 servo on GPIO 27 (see WIRING_GUIDE.md). A stepper is not required to
complete the project — it is here for students who want to add a motorised
device of their own. See EXTENSION_GUIDE.md for how to wire a new device
into the listener and the iPad app.

POWER WARNING
    A 28BYJ-48 can pull well over 200 mA while stepping. Do not run it from
    the Pi's 5V pin alongside the two servos — it will brown out the Pi and
    reset it mid-lesson. Give the ULN2003 its own 5V supply and connect that
    supply's ground to a Pi GND pin so the two share a common ground.

WIRING (ULN2003 driver board)
    Pi GPIO 5  (pin 29) --- IN1
    Pi GPIO 6  (pin 31) --- IN2
    Pi GPIO 13 (pin 33) --- IN3
    Pi GPIO 19 (pin 35) --- IN4
    External 5V (+)     --- driver board  +
    External 5V (GND)   --- driver board  -   AND a Pi GND pin

    These four pins are free in the standard build. Do NOT use GPIO 27, 17
    or 23 — they are the garage servo, the light and the front door servo.

RUN
    Stop the service first so it is not holding the GPIO pins:
        sudo systemctl stop simpsons-house.service
        python3 extensions/stepper_test.py
"""

import time
import RPi.GPIO as GPIO

# IN1-IN4 on the ULN2003 board. Chosen to avoid the pins the standard
# build already uses (17 light, 23 front door servo, 27 garage servo).
STEPPER_PINS = [5, 6, 13, 19]

# Half-step sequence: eight patterns giving smoother, stronger movement
# than four-step. Each inner list is the on/off state of IN1-IN4.
STEP_SEQUENCE = [
    [1, 0, 0, 1],
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
]


def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in STEPPER_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)


def step(sequence, delay, steps):
    """Run through the coil sequence `steps` times, then de-energise."""
    for _ in range(steps):
        for pattern in sequence:
            for pin, value in zip(STEPPER_PINS, pattern):
                GPIO.output(pin, value)
            time.sleep(delay)
    # Always leave the coils off — a stationary energised stepper gets hot
    for pin in STEPPER_PINS:
        GPIO.output(pin, 0)


def main():
    print("Stepper Motor Test (extension hardware)")
    print(f"Using GPIO pins {STEPPER_PINS} as IN1-IN4")
    print("Make sure the ULN2003 has its own 5V supply with a common ground.\n")

    setup()
    try:
        print("Rotating forward one revolution...")
        step(STEP_SEQUENCE, 0.002, 512)
        print("Rotating reverse one revolution...")
        step(list(reversed(STEP_SEQUENCE)), 0.002, 512)
        print("\nStepper motor test complete.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        for pin in STEPPER_PINS:
            GPIO.output(pin, 0)
        GPIO.cleanup()


if __name__ == "__main__":
    main()
