#!/usr/bin/env python3
"""
🏠 Simpson's House GPIO Test Script
Tests all GPIO pins to verify wiring before running MQTT system

This script tests the exact GPIO configuration used in the Simpson's House
Smart Home Control project to ensure proper hardware setup.
"""

import RPi.GPIO as GPIO
import time
import sys

# GPIO pin assignments (BCM numbering) - Simpson's House Configuration
LIGHT_PIN = 17  # Living Room Light (Pin 11)
FAN_PIN = 27    # Ceiling Fan (Pin 13)  
SERVO_PIN = 22  # Front Door Servo (Pin 15)

class SimpsonsHouseGPIOTest:
    def __init__(self):
        """Initialize GPIO settings for Simpson's House"""
        print("🏠 Simpson's House GPIO Test")
        print("=" * 40)
        print("Testing GPIO configuration for Smart Home Control")
        print()
        
        # Set GPIO mode to BCM (Broadcom chip-specific pin numbers)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins
        GPIO.setup(LIGHT_PIN, GPIO.OUT)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        
        # Initialize servo PWM (50Hz for standard servos)
        self.servo_pwm = GPIO.PWM(SERVO_PIN, 50)
        
        print(f"💡 Living Room Light: GPIO {LIGHT_PIN} (Pin 11)")
        print(f"🌀 Ceiling Fan: GPIO {FAN_PIN} (Pin 13)")
        print(f"🚪 Front Door Servo: GPIO {SERVO_PIN} (Pin 15)")
        print("-" * 40)

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
        
        print("-" * 40)

    def test_ceiling_fan(self):
        """Test the ceiling fan (GPIO 27)"""
        print("🌀 Testing Ceiling Fan (GPIO 27)...")
        print("   Watch for fan LED to blink!")
        
        try:
            for i in range(3):
                print(f"   Fan ON (cycle {i+1}/3)")
                GPIO.output(FAN_PIN, GPIO.HIGH)
                time.sleep(1)
                
                print(f"   Fan OFF (cycle {i+1}/3)")
                GPIO.output(FAN_PIN, GPIO.LOW)
                time.sleep(1)
            
            print("✅ Ceiling Fan test completed")
            
        except Exception as e:
            print(f"❌ Ceiling Fan test failed: {e}")
        
        print("-" * 40)

    def test_front_door_servo(self):
        """Test the front door servo (GPIO 22)"""
        print("🚪 Testing Front Door Servo (GPIO 22)...")
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
        
        print("-" * 40)

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
            print("   📱 iOS App → home/fan ON")
            GPIO.output(FAN_PIN, GPIO.HIGH)
            time.sleep(1)
            
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
            GPIO.output(FAN_PIN, GPIO.LOW)
            self.servo_pwm.ChangeDutyCycle(2)  # Close door
            time.sleep(2)
            self.servo_pwm.ChangeDutyCycle(0)
            self.servo_pwm.stop()
            
            print("✅ MQTT simulation completed")
            
        except Exception as e:
            print(f"❌ MQTT simulation failed: {e}")
        
        print("-" * 40)

    def display_wiring_guide(self):
        """Display the wiring diagram for Simpson's House"""
        print("🔌 Simpson's House Wiring Guide:")
        print()
        print("💡 Living Room Light (GPIO 17 - Pin 11):")
        print("   GPIO 17 → 220Ω Resistor → LED (+)")
        print("   LED (-) → GND (Pin 9)")
        print()
        print("🌀 Ceiling Fan (GPIO 27 - Pin 13):")
        print("   GPIO 27 → 220Ω Resistor → LED (+)")
        print("   LED (-) → GND (Pin 14)")
        print()
        print("🚪 Front Door Servo (GPIO 22 - Pin 15):")
        print("   GPIO 22 → Servo Signal (Yellow/Orange)")
        print("   5V (Pin 4) → Servo VCC (Red)")
        print("   GND (Pin 6) → Servo GND (Brown/Black)")
        print()
        print("⚠️  Safety Notes:")
        print("   • Always use 220Ω resistors with LEDs")
        print("   • Servo needs 5V power, not 3.3V")
        print("   • Double-check connections before powering on")
        print("   • Use 'pinout' command to verify pin numbers")
        print("-" * 40)

    def run_all_tests(self):
        """Run all Simpson's House GPIO tests"""
        print("🧪 Starting Simpson's House GPIO Test Suite")
        print("Watch your hardware and verify each device responds!")
        print()
        
        self.display_wiring_guide()
        self.test_living_room_light()
        self.test_ceiling_fan()
        self.test_front_door_servo()
        self.test_mqtt_simulation()
        
        print("🎉 All Simpson's House tests completed!")
        print()
        print("Expected Results:")
        print("✅ Living Room Light LED should have blinked 3 times")
        print("✅ Ceiling Fan LED should have blinked 3 times")
        print("✅ Front Door Servo should have moved through full range")
        print("✅ All devices should respond to simulated MQTT commands")
        print()
        print("If any device didn't work:")
        print("🔍 Check your wiring against the guide above")
        print("🔍 Verify component values (220Ω resistors)")
        print("🔍 Ensure servo has 5V power connection")
        print("🔍 Use 'pinout' command to verify GPIO pin numbers")
        print()
        print("Next Steps:")
        print("🚀 If all tests passed, run: ./setup.sh")
        print("📱 Then test with the iOS Swift Playgrounds app")

    def cleanup(self):
        """Clean up GPIO resources"""
        print()
        print("🧹 Cleaning up GPIO...")
        try:
            if hasattr(self, 'servo_pwm'):
                self.servo_pwm.stop()
        except:
            pass
        GPIO.cleanup()
        print("✅ GPIO cleanup completed")

def test_manual_gpio():
    """Alternative manual GPIO test using filesystem interface"""
    print("🔧 Manual GPIO Test (Alternative Method)")
    print("=" * 40)
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
    print("# Test Ceiling Fan (GPIO 27)")
    print("echo 27 > /sys/class/gpio/export")
    print("echo out > /sys/class/gpio/gpio27/direction")  
    print("echo 1 > /sys/class/gpio/gpio27/value  # Turn ON")
    print("sleep 2")
    print("echo 0 > /sys/class/gpio/gpio27/value  # Turn OFF")
    print("echo 27 > /sys/class/gpio/unexport")

def main():
    """Main function"""
    print("🏠 Welcome to Simpson's House GPIO Testing!")
    print("This script will test your smart home hardware setup.")
    print()
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        test_manual_gpio()
        return
    
    gpio_test = None
    
    try:
        gpio_test = SimpsonsHouseGPIOTest()
        gpio_test.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("\n🔧 Try manual testing with: python3 gpio_test.py --manual")
        
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
