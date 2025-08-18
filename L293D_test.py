#!/usr/bin/env python3
"""
🏠 Simpson's House L293D Motor Test Script
Standalone test for L293D motor driver verification

This script specifically tests the L293D motor driver setup 
before running the full Simpson's House system.
"""

import RPi.GPIO as GPIO
import time
import sys

# GPIO pins (BCM numbering) - L293D Configuration
MOTOR_PIN1 = 27    # L293D Input1 (direction control)
MOTOR_PIN2 = 18    # L293D Input2 (direction control)
MOTOR_ENABLE = 22  # L293D Enable1 (PWM speed control)

class L293DMotorTest:
    def __init__(self):
        """Initialize L293D motor test"""
        print("🌀 L293D Motor Driver Test for Simpson's House")
        print("=" * 45)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup motor control pins
        GPIO.setup(MOTOR_PIN1, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(MOTOR_PIN2, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(MOTOR_ENABLE, GPIO.OUT, initial=GPIO.LOW)
        
        # Setup PWM for speed control
        self.motor_pwm = GPIO.PWM(MOTOR_ENABLE, 1000)  # 1kHz
        
        print(f"🔧 GPIO Pin Configuration:")
        print(f"   Input1 (direction): GPIO {MOTOR_PIN1} → L293D Pin 2")
        print(f"   Input2 (direction): GPIO {MOTOR_PIN2} → L293D Pin 7")
        print(f"   Enable1 (PWM): GPIO {MOTOR_ENABLE} → L293D Pin 1")
        print()

    def display_wiring_check(self):
        """Display L293D wiring checklist"""
        print("📋 L293D Wiring Checklist - Verify Before Testing:")
        print()
        print("🔌 Power Connections:")
        print("   ✓ L293D Pin 16 (VCC) → Pi 5V (Pin 4)")
        print("   ✓ L293D Pin 8 (VMotor) → 9V Battery (+)")
        print("   ✓ L293D Pins 4,5,12,13 (GND) → Pi GND (Pin 6)")
        print("   ✓ 9V Battery (-) → Pi GND (shared ground)")
        print()
        print("🎛️  Control Connections:")
        print(f"   ✓ L293D Pin 1 (Enable1) → Pi GPIO {MOTOR_ENABLE} (Pin 15)")
        print(f"   ✓ L293D Pin 2 (Input1) → Pi GPIO {MOTOR_PIN1} (Pin 13)")
        print(f"   ✓ L293D Pin 7 (Input2) → Pi GPIO {MOTOR_PIN2} (Pin 12)")
        print()
        print("🔧 Motor Connections:")
        print("   ✓ Motor Wire 1 → L293D Pin 3 (Output1)")
        print("   ✓ Motor Wire 2 → L293D Pin 6 (Output2)")
        print()
        print("⚠️  Safety Check:")
        print("   ✓ 9V battery is connected and has charge")
        print("   ✓ All connections are secure")
        print("   ✓ L293D IC is properly seated in breadboard")
        print("   ✓ No short circuits present")
        print()
        
        input("Press Enter when wiring is verified and ready to test...")
        print()

    def set_motor_direction(self, direction):
        """Set motor direction using L293D truth table"""
        if direction == "forward":
            GPIO.output(MOTOR_PIN1, GPIO.HIGH)  # Input1 = HIGH
            GPIO.output(MOTOR_PIN2, GPIO.LOW)   # Input2 = LOW
            return "FORWARD"
        elif direction == "reverse":
            GPIO.output(MOTOR_PIN1, GPIO.LOW)   # Input1 = LOW
            GPIO.output(MOTOR_PIN2, GPIO.HIGH)  # Input2 = HIGH
            return "REVERSE"
        elif direction == "stop":
            GPIO.output(MOTOR_PIN1, GPIO.LOW)   # Input1 = LOW
            GPIO.output(MOTOR_PIN2, GPIO.LOW)   # Input2 = LOW
            return "STOP"
        else:
            return "INVALID"

    def test_motor_basic(self):
        """Test basic motor functionality"""
        print("🧪 Basic Motor Test")
        print("-" * 20)
        
        try:
            self.motor_pwm.start(0)
            
            # Test 1: Motor Forward at 50% speed
            print("Test 1: Motor Forward (50% speed)")
            direction = self.set_motor_direction("forward")
            print(f"   Direction set: {direction}")
            self.motor_pwm.ChangeDutyCycle(50)
            print("   Speed: 50% for 3 seconds")
            time.sleep(3)
            
            # Test 2: Increase speed to 75%
            print("Test 2: Motor Forward (75% speed)")
            self.motor_pwm.ChangeDutyCycle(75)
            print("   Speed: 75% for 2 seconds")
            time.sleep(2)
            
            # Test 3: Stop motor
            print("Test 3: Motor Stop")
            self.motor_pwm.ChangeDutyCycle(0)
            direction = self.set_motor_direction("stop")
            print(f"   Direction: {direction}, Speed: 0%")
            time.sleep(1)
            
            # Test 4: Motor Reverse at 50% speed
            print("Test 4: Motor Reverse (50% speed)")
            direction = self.set_motor_direction("reverse")
            print(f"   Direction set: {direction}")
            self.motor_pwm.ChangeDutyCycle(50)
            print("   Speed: 50% for 3 seconds")
            time.sleep(3)
            
            # Test 5: Final stop
            print("Test 5: Final Stop")
            self.motor_pwm.ChangeDutyCycle(0)
            direction = self.set_motor_direction("stop")
            print(f"   Direction: {direction}, Speed: 0%")
            
            print("✅ Basic motor test completed")
            
        except Exception as e:
            print(f"❌ Basic motor test failed: {e}")
            return False
        
        return True

    def test_speed_control(self):
        """Test PWM speed control"""
        print()
        print("🚀 Speed Control Test")
        print("-" * 20)
        
        try:
            print("Testing speed ramping (Forward direction)")
            self.set_motor_direction("forward")
            
            # Ramp up speed
            for speed in [25, 50, 75, 100]:
                print(f"   Speed: {speed}%")
                self.motor_pwm.ChangeDutyCycle(speed)
                time.sleep(1.5)
            
            # Ramp down speed
            for speed in [75, 50, 25, 0]:
                print(f"   Speed: {speed}%")
                self.motor_pwm.ChangeDutyCycle(speed)
                time.sleep(1)
            
            self.set_motor_direction("stop")
            print("✅ Speed control test completed")
            
        except Exception as e:
            print(f"❌ Speed control test failed: {e}")
            return False
        
        return True

    def test_direction_control(self):
        """Test direction switching"""
        print()
        print("🔄 Direction Control Test")
        print("-" * 20)
        
        try:
            # Test rapid direction changes at medium speed
            self.motor_pwm.ChangeDutyCycle(60)
            
            for cycle in range(3):
                print(f"   Cycle {cycle + 1}: Forward → Stop → Reverse → Stop")
                
                self.set_motor_direction("forward")
                time.sleep(1.5)
                
                self.set_motor_direction("stop")
                time.sleep(0.5)
                
                self.set_motor_direction("reverse")
                time.sleep(1.5)
                
                self.set_motor_direction("stop")
                time.sleep(0.5)
            
            self.motor_pwm.ChangeDutyCycle(0)
            print("✅ Direction control test completed")
            
        except Exception as e:
            print(f"❌ Direction control test failed: {e}")
            return False
        
        return True

    def test_mqtt_simulation(self):
        """Simulate MQTT commands that the main system would send"""
        print()
        print("📡 MQTT Command Simulation")
        print("-" * 25)
        
        try:
            print("Simulating iOS app commands:")
            
            # Simulate: home/fan ON
            print("   📱 Command: home/fan ON")
            self.set_motor_direction("forward")
            self.motor_pwm.ChangeDutyCycle(75)  # Default speed
            print("      → Motor: Forward at 75% speed")
            time.sleep(3)
            
            # Simulate: home/fan OFF
            print("   📱 Command: home/fan OFF")
            self.motor_pwm.ChangeDutyCycle(0)
            self.set_motor_direction("stop")
            print("      → Motor: Stopped")
            time.sleep(1)
            
            # Test multiple ON/OFF cycles
            for i in range(3):
                print(f"   📱 Quick test {i+1}: ON → OFF")
                self.set_motor_direction("forward")
                self.motor_pwm.ChangeDutyCycle(75)
                time.sleep(1)
                self.motor_pwm.ChangeDutyCycle(0)
                self.set_motor_direction("stop")
                time.sleep(0.5)
            
            print("✅ MQTT simulation completed")
            
        except Exception as e:
            print(f"❌ MQTT simulation failed: {e}")
            return False
        
        return True

    def run_full_test(self):
        """Run complete L293D test suite"""
        print("🏠 Starting Complete L293D Test Suite")
        print("Watch and listen for motor movement!")
        print()
        
        self.display_wiring_check()
        
        # Run all tests
        tests_passed = 0
        total_tests = 4
        
        if self.test_motor_basic():
            tests_passed += 1
            
        if self.test_speed_control():
            tests_passed += 1
            
        if self.test_direction_control():
            tests_passed += 1
            
        if self.test_mqtt_simulation():
            tests_passed += 1
        
        # Final results
        print()
        print("=" * 45)
        print(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All L293D tests PASSED!")
            print("✅ Your L293D motor driver is working correctly")
            print("🚀 Ready to run Simpson's House setup: ./setup.sh")
        else:
            print("⚠️  Some tests failed. Check troubleshooting guide below.")
            self.display_troubleshooting()

    def display_troubleshooting(self):
        """Display troubleshooting guide"""
        print()
        print("🔧 L293D Troubleshooting Guide:")
        print()
        print("❌ No motor movement:")
        print("   • Check 9V battery connection and charge level")
        print("   • Verify all GND connections (Pi + Battery + L293D)")
        print("   • Ensure L293D VCC (Pin 16) connected to Pi 5V")
        print("   • Test Enable pin with multimeter (should show 3.3V when active)")
        print()
        print("🔄 Wrong direction:")
        print("   • Swap Input1 and Input2 connections")
        print("   • Or swap motor wires at L293D outputs")
        print()
        print("⚡ Weak/slow motor:")
        print("   • Check battery voltage (should be 9V+)")
        print("   • Verify motor is appropriate for L293D (≤600mA)")
        print("   • Check for loose connections")
        print()
        print("🔥 L293D overheating:")
        print("   • Normal to be warm, but shouldn't be too hot to touch")
        print("   • Ensure good ventilation")
        print("   • Check motor current draw")
        print("   • Verify all ground connections")

    def cleanup(self):
        """Clean up GPIO"""
        try:
            self.motor_pwm.ChangeDutyCycle(0)
            self.set_motor_direction("stop")
            self.motor_pwm.stop()
        except:
            pass
        GPIO.cleanup()
        print()
        print("🧹 GPIO cleanup completed")

def main():
    """Main function"""
    print("🌀 L293D Motor Driver Test for Simpson's House")
    print("This will test your L293D motor driver setup.")
    print()
    
    test = None
    
    try:
        test = L293DMotorTest()
        test.run_full_test()
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Check your wiring and try again")
        
    finally:
        if test:
            test.cleanup()

if __name__ == "__main__":
    # Check GPIO library
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("❌ RPi.GPIO library not found")
        print("Install with: sudo apt-get install python3-rpi.gpio")
        sys.exit(1)
    
    main()
