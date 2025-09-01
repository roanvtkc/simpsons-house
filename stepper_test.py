#!/usr/bin/env python3
"""
🏠 Simpson's House Stepper Motor Test Script
Verifies basic operation of a 28BYJ-48 stepper motor using ULN2003 driver.
"""

import RPi.GPIO as GPIO
import time

STEPPER_PINS = [27, 18, 22, 24]  # IN1-IN4

STEP_SEQUENCE = [
    [1,0,0,1],
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1]
]

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in STEPPER_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)

def step(sequence, delay, steps):
    for _ in range(steps):
        for pattern in sequence:
            for pin, value in zip(STEPPER_PINS, pattern):
                GPIO.output(pin, value)
            time.sleep(delay)
    for pin in STEPPER_PINS:
        GPIO.output(pin, 0)

def main():
    print("🌀 Stepper Motor Test for Simpson's House")
    setup()
    try:
        print("Rotating forward one revolution...")
        step(STEP_SEQUENCE, 0.002, 512)
        print("Rotating reverse one revolution...")
        step(list(reversed(STEP_SEQUENCE)), 0.002, 512)
        print("✅ Stepper motor test complete")
    except KeyboardInterrupt:
        pass
    finally:
        for pin in STEPPER_PINS:
            GPIO.output(pin, 0)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
