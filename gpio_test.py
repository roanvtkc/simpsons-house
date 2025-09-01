#!/usr/bin/env python3
"""
🏠 Simpson's House GPIO Test Script with Stepper Motor
Verifies LED, stepper motor and servo wiring before running the full system.
"""

import RPi.GPIO as GPIO
import time

# GPIO pin assignments (BCM)
LIGHT_PIN = 17
STEPPER_PINS = [27, 18, 22, 24]  # IN1‑IN4
SERVO_PIN = 23

# Half‑step sequence for 28BYJ‑48
STEP_SEQUENCE = [
    [1, 0, 0, 1],
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1]
]

class SimpsonsHouseGPIOTest:
    def __init__(self):
        print("🏠 Simpson's House GPIO Test (Stepper Edition)")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(LIGHT_PIN, GPIO.OUT)
        for pin in STEPPER_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        self.servo_pwm = GPIO.PWM(SERVO_PIN, 50)
        self.servo_pwm.start(0)

    def test_light(self):
        print("💡 Testing light on GPIO 17")
        for _ in range(3):
            GPIO.output(LIGHT_PIN, 1)
            time.sleep(0.5)
            GPIO.output(LIGHT_PIN, 0)
            time.sleep(0.5)
        print("✅ Light test complete")

    def stepper_step(self, sequence, steps, delay=0.002):
        for _ in range(steps):
            for pattern in sequence:
                for pin, value in zip(STEPPER_PINS, pattern):
                    GPIO.output(pin, value)
                time.sleep(delay)
        for pin in STEPPER_PINS:
            GPIO.output(pin, 0)

    def test_stepper(self):
        print("🌀 Testing stepper motor")
        self.stepper_step(STEP_SEQUENCE, 128)
        self.stepper_step(list(reversed(STEP_SEQUENCE)), 128)
        print("✅ Stepper test complete")

    def set_servo_angle(self, angle):
        duty = (angle / 180.0) * 10 + 2
        self.servo_pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)

    def test_servo(self):
        print("🚪 Testing servo")
        self.set_servo_angle(0)
        time.sleep(0.5)
        self.set_servo_angle(90)
        time.sleep(0.5)
        self.set_servo_angle(0)
        print("✅ Servo test complete")

    def cleanup(self):
        self.servo_pwm.stop()
        for pin in STEPPER_PINS:
            GPIO.output(pin, 0)
        GPIO.cleanup()


def main():
    test = SimpsonsHouseGPIOTest()
    try:
        test.test_light()
        test.test_stepper()
        test.test_servo()
    finally:
        test.cleanup()
        print("🏁 GPIO tests completed")

if __name__ == '__main__':
    main()
