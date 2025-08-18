🏠 Simpson's House Smart Home Control
A comprehensive smart home automation project that allows you to control LEDs, DC motors via L293D driver, and servos on a Raspberry Pi directly from an iOS Swift Playgrounds app using MQTT over WebSocket.

Show Image
Show Image
Show Image
Show Image
Show Image

Show Image

✨ Features
🏠 Smart Home Control: Complete home automation system inspired by The Simpsons
📱 iOS App: Beautiful SwiftUI interface built for Swift Playgrounds
🌐 MQTT over WebSocket: Modern, reliable communication protocol
🔧 GPIO Control: Direct hardware control of LEDs, DC motors, and servo motors
⚙️ L293D Motor Driver: Professional motor control with direction and speed
📡 Real-time Communication: Instant response and status feedback
🔄 Auto-reconnection: Robust connection handling with keep-alive pings
🕵️ mDNS Discovery: Automatic network device discovery
⚙️ Systemd Integration: Professional service management
🏗️ System Architecture
mermaid
graph TD
    A[iOS Swift Playgrounds App] -->|WebSocket| B[Mosquitto MQTT Broker]
    B -->|TCP| C[Python MQTT Listener]
    C -->|GPIO| D[Raspberry Pi Hardware]
    
    D --> E[💡 Living Room Light<br/>GPIO 17]
    D --> F[🌀 DC Motor via L293D<br/>GPIO 27, 18, 22]
    D --> G[🚪 Front Door Servo<br/>GPIO 23]
📋 Prerequisites
Raspberry Pi running Raspberry Pi OS (32-bit or 64-bit)
SSH access to the Pi (default credentials: pi/tkcraspberry)
Git installed on the Pi (will be installed automatically if missing)
iOS device with Swift Playgrounds 4+ or macOS with Xcode 13+
Hardware components: LEDs, resistors, L293D motor driver, DC motor, servo motor, breadboard
External power supply: 9V battery or adjustable power supply for motor
Same network: Both devices must be on the same local network
🚀 Quick Start
0. Certificate Installation (Corporate Networks Only)
If you're in a corporate environment with FortiGate firewalls or other SSL inspection systems, you may encounter certificate verification errors like:

bash
fatal: unable to access 'https://github.com/...': server certificate verification failed. CAfile: none CRLfile: none
Quick Certificate Installation:

bash
# Download and run the certificate installer
wget http://10.20.1.83:8081/install_ca.sh
chmod +x install_ca.sh
./install_ca.sh
1. Hardware Setup
🔌 GPIO Pin Layout (BCM Numbering)
    3V3  (1) (2)  5V
  GPIO2  (3) (4)  5V
  GPIO3  (5) (6)  GND
  GPIO4  (7) (8)  GPIO14
    GND  (9) (10) GPIO15
 GPIO17 (11) (12) GPIO18
 GPIO27 (13) (14) GND
 GPIO22 (15) (16) GPIO23
    3V3 (17) (18) GPIO24
 GPIO10 (19) (20) GND
  GPIO9 (21) (22) GPIO25
 GPIO11 (23) (24) GPIO8
    GND (25) (26) GPIO7
  GPIO0 (27) (28) GPIO1
  GPIO5 (29) (30) GND
  GPIO6 (31) (32) GPIO12
 GPIO13 (33) (34) GND
 GPIO19 (35) (36) GPIO16
 GPIO26 (37) (38) GPIO20
    GND (39) (40) GPIO21
🔧 Wiring Diagram
💡 Living Room Light (GPIO 17 - Pin 11):

GPIO 17 (Pin 11) ──── 220Ω Resistor ──── LED (+) 
                                         LED (-) ──── GND (Pin 9)
🌀 DC Motor with L293D Driver:

L293D Pin Layout (16-pin DIP):
                ┌─────────┐
    Enable1  1 │         │ 16  VCC (+5V from external supply)
    Input1   2 │         │ 15  Input4
    Output1  3 │         │ 14  Output4
       GND   4 │ L293D   │ 13  GND
       GND   5 │         │ 12  GND
    Output2  6 │         │ 11  Output3
    Input2   7 │         │ 10  Input3
   VMotor    8 │         │  9  Enable2
                └─────────┘

Connections:
GPIO 27 (Pin 13) ──── L293D Pin 2 (Input1)
GPIO 18 (Pin 12) ──── L293D Pin 7 (Input2)  
GPIO 22 (Pin 15) ──── L293D Pin 1 (Enable1)
5V (Pin 4) ──────── L293D Pin 16 (VCC)
External 9V+ ────── L293D Pin 8 (VMotor)
GND (Pin 6) ─────── L293D Pins 4,5,12,13 (All GND)
DC Motor ────────── L293D Pins 3,6 (Output1,Output2)
🚪 Front Door Servo (GPIO 23 - Pin 16):

GPIO 23 (Pin 16) ──── Servo Signal (Yellow/Orange)
5V (Pin 4) ──────────── Servo VCC (Red)
GND (Pin 6) ─────────── Servo GND (Brown/Black)
📋 Component List
Component	Quantity	Notes
LED (any color)	1	For light indication
220Ω Resistor	1	For LED current limiting
L293D Motor Driver IC	1	16-pin DIP package
DC Motor (3-6V)	1	Small hobby motor
Servo Motor (SG90)	1	Standard 3-wire servo
Breadboard	1	For prototyping
Jumper Wires	15+	Male-to-female recommended
9V Battery + Cable	1	External power for motor
Breadboard Power Module	1	Optional, for cleaner power distribution
⚠️ Safety Notes
External Power Required: L293D motor driver requires external power supply (9V battery)
Never use Pi power for motors: High current draw can damage your Raspberry Pi
Double-check connections before powering on
Use appropriate resistors to prevent LED burnout
L293D Heat: IC may get warm during operation - ensure adequate ventilation
Motor Direction: Test motor direction before final assembly
Common Ground: Pi GND and external power GND must be connected
🔍 Pin Verification
Use this command to see the physical pin layout:

bash
pinout
2. Raspberry Pi Setup
Install Git (if needed):

On your Raspberry Pi, if you see git: command not found when trying to clone:

bash
sudo apt update
sudo apt install -y git
Clone the repository:

bash
git clone https://github.com/roanvtkc/simpsons-house.git
cd simpsons-house
Run the automated setup:

bash
chmod +x setup.sh
./setup.sh
The setup script will:

✅ Install all required packages (including git if missing)
✅ Configure MQTT with WebSocket support (ports 1883 and 9001)
✅ Set up Python environment and GPIO control
✅ Create systemd services for automatic startup
✅ Configure mDNS for device discovery
✅ Test all components
3. iOS App Setup
Open Swift Playgrounds on your iOS device
Create a new playground or import the provided Swift package
Copy the Simpson's House app code into your playground
Update the IP address if needed (the app defaults to 192.168.5.115)
Run the app and grant Local Network permissions when prompted
🎮 Using the App
Connection
Tap "Connect to House" to establish MQTT over WebSocket connection
Wait for "🏠 Simpson's House Connected!" status
Start controlling your devices!
Device Controls
💡 Living Room Light: Toggle the main lighting
🌀 Ceiling Fan: Control motor with direction and speed
ON: Motor runs forward at full speed
OFF: Motor stops
Future: Variable speed control via PWM
🚪 Front Door: Operate the servo-controlled entrance
Features
📊 Real-time status: See device states instantly
📋 Activity logs: Monitor all commands and responses
ℹ️ System info: View hardware and network configuration
🔄 Auto-reconnect: Automatic connection recovery
🛠️ Configuration
MQTT Topics
Topic	Description	Commands
home/light	Living room light control	ON, OFF
home/fan	DC motor control via L293D	ON (forward), OFF (stop)
home/door	Front door servo	ON (open), OFF (close)
Network Ports
1883: MQTT TCP (standard MQTT clients)
9001: MQTT WebSocket (iOS app)
Service Management
bash
# Check status
sudo systemctl status simpsons-house
sudo systemctl status mosquitto

# View logs
sudo journalctl -u simpsons-house -f
sudo journalctl -u mosquitto -f

# Restart services
sudo systemctl restart simpsons-house
sudo systemctl restart mosquitto

# Test MQTT manually
mosquitto_pub -h localhost -t home/light -m ON
mosquitto_pub -h localhost -t home/fan -m ON
mosquitto_sub -h localhost -t home/# -v
🔧 Advanced Configuration
Custom GPIO Pins
Edit mqttlistener.py to change pin assignments:

python
# GPIO pin assignments (BCM numbering)
LIGHT_PIN = 17     # Light control
MOTOR_PIN1 = 27    # L293D Input1 (direction)
MOTOR_PIN2 = 18    # L293D Input2 (direction)
MOTOR_ENABLE = 22  # L293D Enable1 (PWM speed)
SERVO_PIN = 23     # Servo control
Motor Speed Control
The L293D setup supports PWM speed control. Future updates can include:

python
# Variable speed control (0-100%)
def set_motor_speed(speed_percent):
    motor_pwm.ChangeDutyCycle(speed_percent)
Network Settings
Update the iOS app host address:

swift
@StateObject private var mqttClient = SimpsonsHouseMQTTClient(host: "YOUR_PI_IP_ADDRESS")
🧪 Testing & Verification
Test GPIO Pins Before MQTT Setup
Create a simple GPIO test script:

bash
cd ~/simpsons-house
nano l293d_test.py
Copy this L293D test script:

python
#!/usr/bin/env python3
"""
Simpson's House L293D Motor Test Script
Tests L293D motor driver and servo control
"""
import RPi.GPIO as GPIO
import time

# GPIO pins (BCM numbering)
LIGHT_PIN = 17
MOTOR_PIN1 = 27    # L293D Input1
MOTOR_PIN2 = 18    # L293D Input2  
MOTOR_ENABLE = 22  # L293D Enable1
SERVO_PIN = 23

def test_l293d_motor():
    print("🏠 Simpson's House L293D Motor Test")
    print("=" * 40)
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup pins
    GPIO.setup(LIGHT_PIN, GPIO.OUT)
    GPIO.setup(MOTOR_PIN1, GPIO.OUT)
    GPIO.setup(MOTOR_PIN2, GPIO.OUT)
    GPIO.setup(MOTOR_ENABLE, GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    
    # Setup PWM for motor speed control
    motor_pwm = GPIO.PWM(MOTOR_ENABLE, 1000)  # 1kHz
    servo_pwm = GPIO.PWM(SERVO_PIN, 50)       # 50Hz
    
    try:
        print("🧪 Testing all devices...")
        
        # Test Light
        print("💡 Testing Light...")
        GPIO.output(LIGHT_PIN, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(LIGHT_PIN, GPIO.LOW)
        
        # Test Motor Forward
        print("🌀 Testing Motor Forward...")
        GPIO.output(MOTOR_PIN1, GPIO.HIGH)
        GPIO.output(MOTOR_PIN2, GPIO.LOW)
        motor_pwm.start(75)  # 75% speed
        time.sleep(3)
        motor_pwm.stop()
        
        # Test Motor Reverse
        print("🔄 Testing Motor Reverse...")
        GPIO.output(MOTOR_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_PIN2, GPIO.HIGH)
        motor_pwm.start(75)  # 75% speed
        time.sleep(3)
        motor_pwm.stop()
        
        # Stop Motor
        print("🛑 Stopping Motor...")
        GPIO.output(MOTOR_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_PIN2, GPIO.LOW)
        
        # Test Servo
        print("🚪 Testing Servo...")
        servo_pwm.start(0)
        servo_pwm.ChangeDutyCycle(2)   # 0 degrees
        time.sleep(1)
        servo_pwm.ChangeDutyCycle(7)   # 90 degrees
        time.sleep(1)
        servo_pwm.ChangeDutyCycle(2)   # 0 degrees
        time.sleep(1)
        servo_pwm.stop()
        
        print("✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    finally:
        motor_pwm.stop()
        servo_pwm.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    test_l293d_motor()
Run the L293D test:

bash
python3 l293d_test.py
Expected Results:
💡 Light LED: Should turn ON for 2 seconds, then OFF
🌀 DC Motor: Should run forward for 3 seconds, then reverse for 3 seconds, then stop
🚪 Servo: Should move from 0° to 90° and back to 0°
Verify Services
bash
# Check MQTT broker
sudo systemctl status mosquitto

# Check listening ports (should show both 1883 and 9001)
sudo netstat -tlnp | grep -E "(1883|9001)"

# Test MQTT broker
mosquitto_pub -h localhost -t test/message -m "Hello Simpson's House"
mosquitto_sub -h localhost -t test/# -v

# Check mDNS discovery
avahi-browse -rt _mqtt._tcp
Test Motor Control
bash
# Test individual devices
mosquitto_pub -h localhost -t home/light -m ON
mosquitto_pub -h localhost -t home/fan -m ON    # Motor forward
mosquitto_pub -h localhost -t home/fan -m OFF   # Motor stop
mosquitto_pub -h localhost -t home/door -m ON   # Servo open
🐛 Troubleshooting
<details> <summary><strong>L293D Motor Issues</strong></summary>
Motor not running:

Check external power supply (9V battery connected?)
Verify L293D IC is properly seated in breadboard
Ensure all GND connections are made (Pi GND to external power GND)
Test with multimeter: Enable pin should show 3.3V when motor command is ON
Motor runs but wrong direction:

Swap Input1 and Input2 connections (GPIO 27 and GPIO 18)
Or swap motor wires at L293D outputs
Motor runs slowly:

Check external power supply voltage (should be 6-12V)
Verify PWM duty cycle in code (should be 75-100% for full speed)
L293D may be overheating - check for adequate cooling
L293D gets hot:

Normal operation - IC can get warm
Ensure adequate ventilation
Consider heat sink for continuous operation
Check motor current draw (should be <600mA per channel)
</details> <details> <summary><strong>GPIO & Hardware Issues</strong></summary>
Check GPIO status:

bash
# See pin layout
pinout

# Check what's using GPIO pins
sudo fuser /dev/gpiomem
Manual L293D testing:

bash
# Test motor control pins
echo 27 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio27/direction
echo 1 > /sys/class/gpio/gpio27/value    # Set direction
echo 22 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio22/direction
echo 1 > /sys/class/gpio/gpio22/value    # Enable motor
# Motor should run - test with multimeter if needed
Common L293D wiring issues:

Pin numbering: Ensure correct L293D pin identification
Power separation: 5V logic power vs. motor power (VMotor)
Ground loops: All grounds must be connected together
Enable pins: Must be HIGH for motor to run
</details>
Log Locations
Setup logs: /tmp/simpsons_house_setup.log
MQTT listener: sudo journalctl -u simpsons-house -f
Mosquitto broker: /var/log/mosquitto/mosquitto.log
System logs: sudo journalctl -f
🔒 Security Considerations
⚠️ Important: This project uses allow_anonymous true for simplicity. For production use:

Enable MQTT authentication with username/password
Use TLS/SSL encryption for MQTT connections
Configure firewall rules to limit access
Regular security updates for all components
Consider VPN access for remote control
📁 Project Structure
simpsons-house/
├── 📄 README.md                    # This file
├── 🔧 setup.sh                     # Automated setup script
├── 🐍 mqttlistener.py               # Python MQTT listener with L293D control
├── 🔐 install_ca.sh                # FortiGate certificate installer
├── 🧪 l293d_test.py                # L293D motor test script
├── 📱 ios-app/                     # Swift Playgrounds app code
│   └── ContentView.swift
├── 📋 systemd/                     # Systemd service files
│   └── simpsons-house.service
└── 📊 docs/                        # Additional documentation
    ├── hardware-setup.md
    ├── troubleshooting.md
    └── api-reference.md
🤝 Contributing
We welcome contributions! Please see our Contributing Guide for details.

Development Setup
Fork the repository
Create a feature branch: git checkout -b feature/amazing-feature
Commit changes: git commit -m 'Add amazing feature'
Push to branch: git push origin feature/amazing-feature
Open a Pull Request
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🎯 Roadmap
Upcoming Features
 Variable motor speed control via PWM
 Motor direction reversal commands
 Current sensing for motor load monitoring
 Temperature sensors and climate control
 Motion detection and security features
 Voice control integration (Siri Shortcuts)
 Web dashboard for browser control
Version History
v3.1 - L293D motor driver integration, improved motor control
v3.0 - MQTT over WebSocket support, systemd integration
v2.0 - Basic MQTT control with GPIO
v1.0 - Initial HTTP-based control system
📞 Support
Getting Help
📖 Check the Documentation
🐛 Report Issues
💬 Discussions
❓ FAQ
Community
🌟 Star this repo if you find it useful!
🐦 Follow updates on Twitter: @SimpsonsHousePi
💡 Share your builds and modifications
Made with ❤️ for smart home enthusiasts and Simpsons fans

For support and questions, please open an issue or check our troubleshooting guide.

