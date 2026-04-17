#!/usr/bin/env python3
"""
🏠 Simpson's House GPIO Test Script
=====================================
Run this script BEFORE starting the full system to verify every device
is wired correctly. Work through each test one at a time.

Usage:
    python3 gpio_test.py

What to watch for is printed before each test so you know exactly
what physical movement to expect from the hardware.
"""

import RPi.GPIO as GPIO
import time

# GPIO pin assignments (BCM numbering — must match mqttlistener.py)
LIGHT_PIN    = 17
STEPPER_PINS = [27, 18, 22, 24]   # Must be in this order: IN1, IN2, IN3, IN4
SERVO_PIN    = 23

# Half-step coil sequence for the 28BYJ-48 stepper motor
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


def print_divider():
    print("─" * 50)


class SimpsonsHouseGPIOTest:

    def __init__(self):
        print()
        print("🏠 Simpson's House GPIO Test")
        print_divider()
        print("Setting up GPIO pins...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(LIGHT_PIN, GPIO.OUT)
        for pin in STEPPER_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)
        GPIO.setup(SERVO_PIN, GPIO.OUT)

        self.servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz for servo
        self.servo_pwm.start(0)
        print("✅ GPIO pins ready")
        print()

    # ── Test 1: LED ──────────────────────────────────────────────────────────

    def test_light(self):
        print("💡 TEST 1/3 — Living Room Light (GPIO 17)")
        print_divider()
        print("   WHAT TO WATCH FOR:")
        print("   → The LED should blink ON and OFF exactly 3 times")
        print("   → Each blink: 0.5 s ON, then 0.5 s OFF")
        print()
        print("   If nothing happens:")
        print("   • Check the LED is the right way around (long leg toward GPIO 17)")
        print("   • Check the resistor is in the circuit (between GPIO 17 and the LED +)")
        print("   • Verify GPIO 17 is on physical pin 11 (run 'pinout' to check)")
        print()

        input("   Press ENTER when you are watching the LED...")
        print()

        for blink in range(1, 4):
            print(f"   Blink {blink}/3 — ON")
            GPIO.output(LIGHT_PIN, 1)
            time.sleep(0.5)
            print(f"   Blink {blink}/3 — OFF")
            GPIO.output(LIGHT_PIN, 0)
            time.sleep(0.5)

        print()
        response = input("   Did the LED blink 3 times? (y/n): ").strip().lower()
        if response == "y":
            print("   ✅ Light test PASSED")
        else:
            print("   ❌ Light test FAILED — check WIRING_GUIDE.md → Device 1")
        print()

    # ── Test 2: Stepper Motor ────────────────────────────────────────────────

    def stepper_step(self, sequence, steps, delay=0.002):
        """Run the stepper motor for a given number of steps."""
        for _ in range(steps):
            for pattern in sequence:
                for pin, value in zip(STEPPER_PINS, pattern):
                    GPIO.output(pin, value)
                time.sleep(delay)
        # De-energise all coils when done
        for pin in STEPPER_PINS:
            GPIO.output(pin, 0)

    def test_stepper(self):
        print("🌀 TEST 2/3 — Garage Door Stepper Motor (GPIO 27, 18, 22, 24)")
        print_divider()
        print("   WHAT TO WATCH FOR:")
        print("   → The motor shaft (small white gear) should rotate ONE direction")
        print("     for about 2 seconds, then REVERSE direction for 2 seconds")
        print("   → You will hear a faint buzzing/clicking sound")
        print()
        print("   If the motor vibrates but doesn't spin:")
        print("   • The IN1–IN4 wires may be in the wrong order")
        print("   • Double-check: GPIO 27→IN1, GPIO 18→IN2, GPIO 22→IN3, GPIO 24→IN4")
        print()
        print("   If nothing moves at all:")
        print("   • Check 5V is connected to ULN2003 VCC")
        print("   • Check GND is connected to ULN2003 GND")
        print("   • Check the motor white plug is fully seated in the ULN2003 board")
        print()

        input("   Press ENTER when you are watching the motor shaft...")
        print()

        print("   ▶ Rotating FORWARD (128 steps)...")
        self.stepper_step(STEP_SEQUENCE, 128)
        time.sleep(0.5)

        print("   ◀ Rotating REVERSE (128 steps)...")
        self.stepper_step(list(reversed(STEP_SEQUENCE)), 128)
        time.sleep(0.5)

        print()
        response = input("   Did the motor rotate forward then reverse? (y/n): ").strip().lower()
        if response == "y":
            print("   ✅ Stepper test PASSED")
        else:
            print("   ❌ Stepper test FAILED — check WIRING_GUIDE.md → Device 2")
        print()

    # ── Test 3: Servo ────────────────────────────────────────────────────────

    def set_servo_angle(self, angle):
        """Move servo to specified angle (0–180°)."""
        duty = (angle / 180.0) * 10 + 2  # Maps 0–180° to 2–12% duty cycle
        self.servo_pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)  # Stop PWM signal to prevent jitter

    def test_servo(self):
        print("🚪 TEST 3/3 — Front Door Servo (GPIO 23)")
        print_divider()
        print("   WHAT TO WATCH FOR:")
        print("   → The servo arm should move smoothly to 90° (open position)")
        print("   → Hold for half a second")
        print("   → Then sweep back to 0° (closed position)")
        print()
        print("   If the servo twitches but doesn't hold position:")
        print("   • Check the red power wire is connected to 5V (physical pin 4)")
        print()
        print("   If nothing moves:")
        print("   • Check the signal wire (orange/yellow/white) → GPIO 23 (physical pin 16)")
        print("   • Check the ground wire (brown/black) → Pi GND (physical pin 6)")
        print()
        print("   If the arm moves the wrong way:")
        print("   • The servo may be mounted upside-down — that is fine for testing")
        print("   • You can flip the physical servo, or change the angle in control_door()")
        print()

        input("   Press ENTER when you are watching the servo arm...")
        print()

        print("   → Moving to 0°  (closed / starting position)...")
        self.set_servo_angle(0)
        time.sleep(0.5)

        print("   → Moving to 90° (open position)...")
        self.set_servo_angle(90)
        time.sleep(0.5)

        print("   → Returning to 0° (closed position)...")
        self.set_servo_angle(0)
        time.sleep(0.3)

        print()
        response = input("   Did the servo arm move to 90° then return to 0°? (y/n): ").strip().lower()
        if response == "y":
            print("   ✅ Servo test PASSED")
        else:
            print("   ❌ Servo test FAILED — check WIRING_GUIDE.md → Device 3")
        print()

    # ── Cleanup ──────────────────────────────────────────────────────────────

    def cleanup(self):
        self.servo_pwm.stop()
        for pin in STEPPER_PINS:
            GPIO.output(pin, 0)
        GPIO.cleanup()


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    test = SimpsonsHouseGPIOTest()
    results = {"light": False, "stepper": False, "servo": False}

    try:
        test.test_light()
        test.test_stepper()
        test.test_servo()

    finally:
        test.cleanup()

    # Final summary
    print_divider()
    print("🏁 GPIO Test Complete")
    print()
    print("   If all three tests passed you are ready to run the full system:")
    print()
    print("   sudo systemctl start simpsons-house")
    print()
    print("   Then open the iPad app and tap 'Connect to House'.")
    print()
    print("   If any test failed, check WIRING_GUIDE.md for that device")
    print("   and re-run this script after fixing the wiring.")
    print_divider()


if __name__ == "__main__":
    main()
