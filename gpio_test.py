#!/usr/bin/env python3
"""
🏠 Simpson's House GPIO Test Script with L293D Motor Driver
Tests all GPIO pins to verify wiring before running MQTT system

This script tests the exact GPIO configuration used in the Simpson's House
Smart Home Control project with L293D motor driver integration.
"""

import RPi.GPIO as GPIO
import time
import sys

# GPIO pin assignments (BCM numbering) - Simpson's House L293D Configuration
LIGHT_PIN = 17     # Living Room Light (Pin 11)
MOTOR_PIN1 = 27    # L293D Input1 (Pin 13) - Direction Control
MOTOR_PIN2 = 18    # L293D Input2 (Pin 12) - Direction Control  
MOTOR_ENABLE = 22  # L293D Enable1 (Pin 15) - PWM Speed Control
SERVO_PIN = 23     # Front Door Servo (Pin 16) - Moved from GPIO 22

class SimpsonsHouseL293DGPIOTest:
    def __init__(self):
        """Initialize GPIO settings for Simpson's House with L293D"""
        print("🏠 Simpson's House GPIO Test with L293D Motor Driver")
        print("=" * 50)
        print("Testing GPIO configuration for Smart Home Control v3.1")
        print()
        
        # Set GPIO mode to BCM (Broadcom chip-specific pin numbers)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins
        GPIO.setup(LIGHT_PIN, GPIO.OUT)
        GPIO.setup(MOTOR_PIN1, GPIO.OUT)
        GPIO.setup(MOTOR_PIN2, GPIO.OUT)
        GPIO.setup(MOTOR_ENABLE, GPIO.OUT)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        
        # Initialize PWM for motor and servo
        self.motor_pwm = GPIO.PWM(MOTOR_ENABLE, 1000)  # 1kHz for motor
        self.servo_pwm = GPIO.PWM(SERVO_PIN, 50)       # 50Hz for servo
        
        print(f"💡 Living Room Light: GPIO {LIGHT_PIN} (Pin 11)")
        print(f"🌀 L293D Motor Driver:")
        print(f"   - Input1 (direction): GPIO {MOTOR_PIN1} (Pin 13)")
        print(f"   - Input2 (direction): GPIO {MOTOR_PIN2} (Pin 12)")
        print(f"   - Enable1 (PWM): GPIO {MOTOR_ENABLE} (Pin 15)")
        print(f"🚪 Front Door Servo: GPIO {SERVO_PIN} (Pin 16)")
        print("-" * 50)

    def test_living_room_light(self):
        """Test the living room light (GPIO 17)"""
        print("💡 Testing Living Room Light (GPIO 17)...")
        print("   Watch for LED to blink!")
        
        try:
            for i in range(3):
                print(f"   Light ON (cycle {i+1}/3)")
                GPIO.output(LIGHT_PIN, GPIO.HIGH)
                time.sleep(1)
                
                print(f"   Light OFF (cycle {i+1}/3)")
                GPIO.output(LIGHT_PIN, GPIO.LOW)
                time.sleep(1)
            
            print("✅ Living Room Light test completed")
            
        except Exception as e:
            print(f"❌ Living Room Light test failed: {e}")
        
        print("-" * 50)

    def set_motor_direction(self, direction):
        """Set L293D motor direction"""
        if direction == "forward":
            GPIO.output(MOTOR_PIN1, GPIO.HIGH)
            GPIO.output(MOTOR_PIN2, GPIO.LOW)
            print("   🔄 Motor direction: FORWARD")
        elif direction == "reverse":
            GPIO.output(MOTOR_PIN1, GPIO.LOW)
            GPIO.output(MOTOR_PIN2, GPIO.HIGH)
            print("   🔄 Motor direction: REVERSE")
        elif direction == "stop":
            GPIO.output(MOTOR_PIN1, GPIO.LOW)
            GPIO.output(MOTOR_PIN2, GPIO.LOW)
            print("   🛑 Motor direction: STOP")

    def test_l293d_motor(self):
        """Test the L293D motor driver with DC motor"""
        print("🌀 Testing L293D Motor Driver...")
        print("   Watch for motor movement and listen for motor sound!")
        print("   ⚠️  Ensure external power supply is connected to L293D!")
        
        try:
            self.motor_pwm.start(0)  # Start PWM at 0%
            
            # Test motor forward direction
            print("   Testing FORWARD direction at 50% speed...")
            self.set_motor_direction("forward")
            self.motor_pwm.ChangeDutyCycle(50)
            time.sleep(3)
            
            # Test motor at higher speed
            print("   Testing FORWARD direction at 75% speed...")
            self.motor_pwm.ChangeDutyCycle(75)
            time.sleep(2)
            
            # Stop motor briefly
            print("   Stopping motor...")
            self.motor_pwm.ChangeDutyCycle(0)
            time.sleep(1)
            
            # Test motor reverse direction
            print("   Testing REVERSE direction at 50% speed...")
            self.set_motor_direction("reverse")
            self.motor_pwm.ChangeDutyCycle(50)
            time.sleep(3)
            
            # Test reverse at higher speed
            print("   Testing REVERSE direction at 75% speed...")
            self.motor_pwm.ChangeDutyCycle(75)
            time.sleep(2)
            
            # Final stop
            print("   Final motor stop...")
            self.motor_pwm.ChangeDutyCycle(0)
            self.set_motor_direction("stop")
            
            self.motor_pwm.stop()
            print("✅ L293D Motor Driver test completed")
            
        except Exception as e:
            print(f"❌ L293D Motor test failed: {e}")
            try:
                self.motor_pwm.ChangeDutyCycle(0)
                self.set_motor_direction("stop")
                self.motor_pwm.stop()
            except:
                pass
        
        print("-" * 50)

    def test_front_door_servo(self):
        """Test the front door servo (GPIO 23)"""
        print("🚪 Testing Front Door Servo (GPIO 23)...")
        print("   Watch for servo movement!")
        
        try:
            self.servo_pwm.start(0)
            
            # Door positions (duty cycle percentages for servo control)
            # 2% = 0 degrees (closed), 7% = 90 degrees (open), 12% = 180 degrees
            
            print("   Door closing (0°)...")
            self.servo_pwm.ChangeDutyCycle(2)  # 0 degrees
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)  # Stop signal
            time.sleep(0.5)
            
            print("   Door opening (90°)...")
            self.servo_pwm.ChangeDutyCycle(7)  # 90 degrees
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)  # Stop signal
            time.sleep(0.5)
            
            print("   Door wide open (180°)...")
            self.servo_pwm.ChangeDutyCycle(12)  # 180 degrees
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)  # Stop signal
            time.sleep(0.5)
            
            print("   Door closing again (0°)...")
            self.servo_pwm.ChangeDutyCycle(2)  # 0 degrees
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)  # Stop signal
            
            self.servo_pwm.stop()
            print("✅ Front Door Servo test completed")
            
        except Exception as e:
            print(f"❌ Front Door Servo test failed: {e}")
            if hasattr(self, 'servo_pwm'):
                self.servo_pwm.stop()
        
        print("-" * 50)

    def test_mqtt_simulation(self):
        """Simulate MQTT commands for all devices"""
        print("📡 Testing MQTT Command Simulation...")
        print("   Simulating commands that the iOS app would send:")
        
        try:
            # Simulate: mosquitto_pub -h localhost -t home/light -m ON
            print("   📱 iOS App → home/light ON")
            GPIO.output(LIGHT_PIN, GPIO.HIGH)
            time.sleep(1)
            
            # Simulate: mosquitto_pub -h localhost -t home/fan -m ON  
            print("   📱 iOS App → home/fan ON (motor forward)")
            self.motor_pwm.start(0)
            self.set_motor_direction("forward")
            self.motor_pwm.ChangeDutyCycle(75)
            time.sleep(3)
            
            # Simulate: mosquitto_pub -h localhost -t home/door -m ON
            print("   📱 iOS App → home/door ON (open)")
            self.servo_pwm.start(0)
            self.servo_pwm.ChangeDutyCycle(7)  # Open door
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)
            time.sleep(1)
            
            # Turn everything off
            print("   📱 iOS App → All devices OFF")
            GPIO.output(LIGHT_PIN, GPIO.LOW)
            self.motor_pwm.ChangeDutyCycle(0)
            self.set_motor_direction("stop")
            self.servo_pwm.ChangeDutyCycle(2)  # Close door
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)
            
            self.motor_pwm.stop()
            self.servo_pwm.stop()
            
            print("✅ MQTT simulation completed")
            
        except Exception as e:
            print(f"❌ MQTT simulation failed: {e}")
        
        print("-" * 50)

    def display_l293d_wiring_guide(self):
        """Display the L293D wiring diagram for Simpson's House"""
        print("🔌 Simpson's House L293D Wiring Guide:")
        print()
        print("💡 Living Room Light (GPIO 17 - Pin 11):")
        print("   GPIO 17 → 220Ω Resistor → LED (+)")
        print("   LED (-) → GND (Pin 9)")
        print()
        print("🌀 L293D Motor Driver Connections:")
        print("   L293D Pin Layout (16-pin DIP):")
        print("                   ┌─────────┐")
        print("       Enable1  1 │         │ 16  VCC (+5V)")
        print("       Input1   2 │         │ 15  Input4")
        print("       Output1  3 │         │ 14  Output4")
        print("          GND   4 │ L293D   │ 13  GND")
        print("          GND   5 │         │ 12  GND")
        print("       Output2  6 │         │ 11  Output3")
        print("       Input2   7 │         │ 10  Input3")
        print("      VMotor   8 │         │  9  Enable2")
        print("                   └─────────┘")
        print()
        print("   🔌 Pi to L293D Connections:")
        print(f"   GPIO {MOTOR_PIN1} (Pin 13) → L293D Pin 2 (Input1)")
        print(f"   GPIO {MOTOR_PIN2} (Pin 12) → L293D Pin 7 (Input2)")
        print(f"   GPIO {MOTOR_ENABLE} (Pin 15) → L293D Pin 1 (Enable1)")
        print("   5V (Pin 4) → L293D Pin 16 (VCC)")
        print("   GND (Pin 6) → L293D Pins 4,5,12,13 (All GND)")
        print()
        print("   ⚡ External Power:")
        print("   9V Battery (+) → L293D Pin 8 (VMotor)")
        print("   9V Battery (-) → Pi GND (shared ground)")
        print()
        print("   🔧 Motor Connections:")
        print("   DC Motor Wire 1 → L293D Pin 3 (Output1)")
        print("   DC Motor Wire 2 → L293D Pin 6 (Output2)")
        print()
        print("🚪 Front Door Servo (GPIO 23 - Pin 16):")
        print("   GPIO 23 → Servo Signal (Yellow/Orange)")
        print("   5V (Pin 4) → Servo VCC (Red)")
        print("   GND (Pin 6) → Servo GND (Brown/Black)")
        print()
        print("⚠️  Safety Notes:")
        print("   • L293D requires external power supply (9V battery)")
        print("   • Never power motor directly from Raspberry Pi")
        print("   • Ensure all grounds are connected together")
        print("   • L293D may get warm during operation")
        print("   • Double-check all connections before powering on")
        print("   • Use 'pinout' command to verify pin numbers")
        print("-" * 50)

    def troubleshooting_guide(self):
        """Display troubleshooting tips for L293D setup"""
        print("🔧 L293D Troubleshooting Guide:")
        print()
        print("❌ Motor not running:")
        print("   • Check 9V battery connection to L293D Pin 8")
        print("   • Verify all GND connections (Pi + battery + L293D)")
        print("   • Ensure Enable pin (GPIO 22) is receiving PWM signal")
        print("   • Test with multimeter: Enable should show 3.3V when ON")
        print()
        print("🔄 Motor running wrong direction:")
        print("   • Swap Input1 and Input2 connections (GPIO 27 ↔ GPIO 18)")
        print("   • Or swap motor wires at L293D Output1 and Output2")
        print()
        print("⚡ Motor running slowly:")
        print("   • Check battery voltage (should be 9V or higher)")
        print("   • Verify PWM duty cycle in code (should be 75-100%)")
        print("   • L293D may be overheating - ensure ventilation")
        print()
        print("🔥 L293D getting hot:")
        print("   • Normal operation - IC can get warm")
        print("   • Ensure adequate air circulation")
        print("   • Check motor current (should be <600mA)")
        print("   • Consider heat sink for continuous operation")
        print()
        print("🔍 Testing Tips:")
        print("   • Use multimeter to test voltages at each pin")
        print("   • Listen for motor humming when enabled")
        print("   • Check LED on breadboard power supply")
        print("   • Verify L293D IC is properly seated")
        print("-" * 50)

    def run_all_tests(self):
        """Run all Simpson's House GPIO tests with L293D"""
        print("🧪 Starting Simpson's House L293D GPIO Test Suite")
        print("Watch your hardware and verify each device responds!")
        print()
        
        self.display_l293d_wiring_guide()
        self.test_living_room_light()
        self.test_l293d_motor()
        self.test_front_door_servo()
        self.test_mqtt_simulation()
        self.troubleshooting_guide()
        
        print("🎉 All Simpson's House L293D tests completed!")
        print()
        print("Expected Results:")
        print("✅ Living Room Light LED should have blinked 3 times")
        print("✅ DC Motor should have run forward and reverse via L293D")
        print("✅ Front Door Servo should have moved through full range")
        print("✅ All devices should respond to simulated MQTT commands")
        print()
        print("If any device didn't work:")
        print("🔍 Check your wiring against the L293D guide above")
        print("🔍 Verify 9V battery is connected to L293D VMotor pin")
        print("🔍 Ensure all grounds are connected together")
        print("🔍 Use 'pinout' command to verify GPIO pin numbers")
        print("🔍 Test L293D with multimeter for proper voltages")
        print()
        print("Next Steps:")
        print("🚀 If all tests passed, run: ./setup.sh")
        print("📱 Then test with the iOS Swift Playgrounds app")
        print("🌀 Motor commands: ON = Forward, OFF = Stop")

    def cleanup(self):
        """Clean up GPIO resources"""
        print()
        print("🧹 Cleaning up GPIO...")
        try:
            # Stop motor safely
            if hasattr(self, 'motor_pwm'):
                self.motor_pwm.ChangeDutyCycle(0)
                self.set_motor_direction("stop")
                self.motor_pwm.stop()
            if hasattr(self, 'servo_pwm'):
                self.servo_pwm.stop()
        except:
            pass
        GPIO.cleanup()
        print("✅ GPIO cleanup completed")

def test_manual_l293d():
    """Alternative manual L293D test using filesystem interface"""
    print("🔧 Manual L293D Test (Alternative Method)")
    print("=" * 50)
    print("This method uses the GPIO filesystem interface")
    print("Run these commands manually if the main test fails:")
    print()
    print("# Test Living Room Light (GPIO 17)")
    print("echo 17 > /sys/class/gpio/export")
    print("echo out > /sys/class/gpio/gpio17/direction")
    print("echo 1 > /sys/class/gpio/gpio17/value  # Turn ON")
    print("sleep 2")
    print("echo 0 > /sys/class/gpio/gpio17/value  # Turn OFF")
    print("echo 17 > /sys/class/gpio/unexport")
    print()
    print("# Test L293D Motor Forward (GPIO 27, 18, 22)")
    print("echo 27 > /sys/class/gpio/export")
    print("echo 18 > /sys/class/gpio/export")
    print("echo 22 > /sys/class/gpio/export")
    print("echo out > /sys/class/gpio/gpio27/direction")
    print("echo out > /sys/class/gpio/gpio18/direction")
    print("echo out > /sys/class/gpio/gpio22/direction")
    print("echo 1 > /sys/class/gpio/gpio27/value   # Input1 HIGH")
    print("echo 0 > /sys/class/gpio/gpio18/value   # Input2 LOW")
    print("echo 1 > /sys/class/gpio/gpio22/value   # Enable HIGH")
    print("sleep 3")
    print("echo 0 > /sys/class/gpio/gpio22/value   # Stop motor")
    print("echo 27 > /sys/class/gpio/unexport")
    print("echo 18 > /sys/class/gpio/unexport")
    print("echo 22 > /sys/class/gpio/unexport")

def main():
    """Main function"""
    print("🏠 Welcome to Simpson's House L293D GPIO Testing!")
    print("This script will test your smart home hardware with L293D motor driver.")
    print()
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        test_manual_l293d()
        return
    
    gpio_test = None
    
    try:
        gpio_test = SimpsonsHouseL293DGPIOTest()
        gpio_test.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("\n🔧 Try manual testing with: python3 gpio_test.py --manual")
        print("🔧 Or check the troubleshooting guide above")
        
    finally:
        if gpio_test:
            gpio_test.cleanup()

if __name__ == "__main__":
    # Check if running on Raspberry Pi with GPIO support
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("❌ Error: RPi.GPIO library not found.")
        print("This script is designed to run on Raspberry Pi.")
        print("Install with: sudo apt-get install python3-rpi.gpio")
        sys.exit(1)
    
    main()
