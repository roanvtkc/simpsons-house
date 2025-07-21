Simpson's House Smart Home Control
A comprehensive smart home automation project that allows you to control LEDs, fans, and servos on a Raspberry Pi directly from an iOS Swift Playgrounds app using MQTT over WebSocket.
Show Image
Show Image
Show Image
✨ Features

🏠 Smart Home Control: Complete home automation system inspired by The Simpsons
📱 iOS App: Beautiful SwiftUI interface built for Swift Playgrounds
🌐 MQTT over WebSocket: Modern, reliable communication protocol
🔧 GPIO Control: Direct hardware control of LEDs, fans, and servo motors
📡 Real-time Communication: Instant response and status feedback
🔄 Auto-reconnection: Robust connection handling with keep-alive pings
🕵️ mDNS Discovery: Automatic network device discovery
⚙️ Systemd Integration: Professional service management

🏗️ System Architecture
iOS Swift Playgrounds App
         ↓ (WebSocket)
    Mosquitto MQTT Broker
         ↓ (TCP)
   Python MQTT Listener
         ↓ (GPIO)
  Raspberry Pi Hardware
📋 Prerequisites

Raspberry Pi running Raspberry Pi OS (32-bit or 64-bit)
SSH access to the Pi
iOS device with Swift Playgrounds 4+ or macOS with Xcode 13+
Hardware components: LEDs, resistors, servo motor, breadboard
Same network: Both devices must be on the same local network

🚀 Quick Start
1. Hardware Setup
Wire your components using BCM pin numbering:
DeviceBCM PinComponentNotes💡 Living Room Light17LED + 220Ω resistorConnect to GND🌀 Ceiling Fan27LED or small fanUse transistor for high current🚪 Front Door22Servo motorSignal pin; power from 5V/GND
⚠️ Safety First: Use appropriate drivers or relays for high-current loads.
2. Raspberry Pi Setup
Clone the repository:
bashgit clone https://github.com/roanvtkc/simpsons-house.git
cd simpsons-house
Run the automated setup:
bashchmod +x setup.sh
./setup.sh
The setup script will:

✅ Install all required packages
✅ Configure MQTT with WebSocket support
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
🌀 Ceiling Fan: Control climate systems
🚪 Front Door: Operate the servo-controlled entrance

Features

📊 Real-time status: See device states instantly
📋 Activity logs: Monitor all commands and responses
ℹ️ System info: View hardware and network configuration
🔄 Auto-reconnect: Automatic connection recovery

🛠️ Configuration
MQTT Topics
TopicDescriptionCommandshome/lightLiving room light controlON, OFFhome/fanCeiling fan controlON, OFFhome/doorFront door servoON (open), OFF (close)
Network Ports

1883: MQTT TCP (standard MQTT clients)
9001: MQTT WebSocket (iOS app)

Service Management
bash# Check status
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
mosquitto_sub -h localhost -t home/# -v
🔧 Advanced Configuration
Custom GPIO Pins
Edit mqttlistener.py to change pin assignments:
python# GPIO pin assignments (BCM numbering)
LIGHT_PIN = 17  # Change to your preferred pin
FAN_PIN   = 27  # Change to your preferred pin  
SERVO_PIN = 22  # Change to your preferred pin
Network Settings
Update the iOS app host address:
swift@StateObject private var mqttClient = SimpsonsHouseMQTTClient(host: "YOUR_PI_IP_ADDRESS")
FortiGate Environments
If you're in a corporate environment with FortiGate firewalls:

The setup script will prompt for certificate installation
Choose 'y' if you need certificate inspection bypass
Choose 'n' for home networks

🧪 Testing & Verification
Verify Services
bash# Check MQTT broker
sudo systemctl status mosquitto

# Check listening ports
sudo netstat -tlnp | grep -E "(1883|9001)"

# Test MQTT broker
mosquitto_pub -h localhost -t test/message -m "Hello Simpson's House"
mosquitto_sub -h localhost -t test/# -v

# Check mDNS discovery
avahi-browse -rt _mqtt._tcp
Test GPIO Control
bash# Test individual devices
mosquitto_pub -h localhost -t home/light -m ON
mosquitto_pub -h localhost -t home/fan -m OFF
mosquitto_pub -h localhost -t home/door -m ON
🐛 Troubleshooting
Common Issues
"Connection timeout" in iOS app:

Verify both devices are on the same WiFi network
Check Pi IP address: hostname -I
Test WebSocket: Use browser to visit ws://PI_IP:9001

"Service failed to start":
bash# Check service logs
sudo journalctl -u simpsons-house -n 50
sudo journalctl -u mosquitto -n 50

# Restart services
sudo systemctl restart mosquitto
sudo systemctl restart simpsons-house
"GPIO permissions denied":

Ensure the script runs as pi user (not root)
Verify user is in gpio group: groups pi

"mDNS discovery not working":

Check Avahi: sudo systemctl status avahi-daemon
Enable Local Network in iOS Settings → Privacy → Local Network
Add _mqtt._tcp service in Swift Playgrounds capabilities

Log Locations

Setup logs: /tmp/simpsons_house_setup.log
MQTT listener: sudo journalctl -u simpsons-house -f
Mosquitto broker: /var/log/mosquitto/mosquitto.log
System logs: sudo journalctl -f

🔒 Security Considerations
⚠️ Important: This project uses allow_anonymous true for simplicity. For production use:

Enable MQTT authentication
Use TLS/SSL encryption
Configure firewall rules
Regular security updates

🤝 Contributing

Fork the repository
Create a feature branch: git checkout -b feature/amazing-feature
Commit changes: git commit -m 'Add amazing feature'
Push to branch: git push origin feature/amazing-feature
Open a Pull Request

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
🎯 Future Enhancements

 Temperature sensors and climate control
 Motion detection and security features
 Voice control integration
 Web dashboard for browser control
 Schedule automation and timers
 Energy monitoring and usage statistics

🏠 About Simpson's House
This project brings the iconic Simpson family home into the smart home era! Control Marge's kitchen lights, Homer's ceiling fan, and the front door security - all from your iPhone or iPad.
"D'oh! Why didn't I think of smart home automation sooner?" - Homer Simpson (probably)

Made with ❤️ for smart home enthusiasts and Simpsons fans
For support and questions, please open an issue on GitHub!
