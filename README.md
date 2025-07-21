<details>
<summary><strong>SSH Issues</strong></summary>

**"Host key verification failed" or "Remote host identification has changed":**
```bash
ssh-keygen -R 192.168.5.115
```
Then retry the SSH connection and accept the new host key when prompted.

**Cannot connect via SSH:**
- Verify SSH is enabled: `sudo systemctl enable ssh`
- Check if SSH service is running: `sudo systemctl status ssh`
- Ensure you're using the correct IP address: `hostname -I`
</details># 🏠 Simpson's House Smart Home Control

A comprehensive smart home automation project that allows you to control LEDs, fans, and servos on a Raspberry Pi directly from an iOS Swift Playgrounds app using **MQTT over WebSocket**.

[![Status](https://img.shields.io/badge/Status-Smart%20Home%20Ready-brightgreen)](https://github.com/roanvtkc/simpsons-house)
[![MQTT](https://img.shields.io/badge/MQTT-WebSocket%20Enabled-blue)](https://mqtt.org/)
[![iOS](https://img.shields.io/badge/iOS-Swift%20Playgrounds-orange)](https://www.apple.com/swift/playgrounds/)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)](https://www.raspberrypi.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

![Simpson's House Banner](https://via.placeholder.com/800x200/FFD700/000000?text=🏠+Simpson's+House+Smart+Home)

## ✨ Features

- **🏠 Smart Home Control**: Complete home automation system inspired by The Simpsons
- **📱 iOS App**: Beautiful SwiftUI interface built for Swift Playgrounds
- **🌐 MQTT over WebSocket**: Modern, reliable communication protocol
- **🔧 GPIO Control**: Direct hardware control of LEDs, fans, and servo motors
- **📡 Real-time Communication**: Instant response and status feedback
- **🔄 Auto-reconnection**: Robust connection handling with keep-alive pings
- **🕵️ mDNS Discovery**: Automatic network device discovery
- **⚙️ Systemd Integration**: Professional service management

## 🏗️ System Architecture

```mermaid
graph TD
    A[iOS Swift Playgrounds App] -->|WebSocket| B[Mosquitto MQTT Broker]
    B -->|TCP| C[Python MQTT Listener]
    C -->|GPIO| D[Raspberry Pi Hardware]
    
    D --> E[💡 Living Room Light<br/>GPIO 17]
    D --> F[🌀 Ceiling Fan<br/>GPIO 27]
    D --> G[🚪 Front Door Servo<br/>GPIO 22]
```

## 📋 Prerequisites

- **Raspberry Pi** running Raspberry Pi OS (32-bit or 64-bit)
- **SSH access** to the Pi (default credentials: `pi`/`tkcraspberry`)
- **Git installed** on the Pi (will be installed automatically if missing)
- **iOS device** with Swift Playgrounds 4+ or macOS with Xcode 13+
- **Hardware components**: LEDs, resistors, servo motor, breadboard
- **Same network**: Both devices must be on the same local network

## 🚀 Quick Start

### 1. Hardware Setup

Wire your components using **BCM pin numbering**:

| Device | BCM Pin | Component | Notes |
|--------|---------|-----------|-------|
| 💡 Living Room Light | 17 | LED + 220Ω resistor | Connect to GND |
| 🌀 Ceiling Fan | 27 | LED or small fan | Use transistor for high current |
| 🚪 Front Door | 22 | Servo motor | Signal pin; power from 5V/GND |

> ⚠️ **Safety First**: Use appropriate drivers or relays for high-current loads.

### 2. Raspberry Pi Setup

**Install Git (if needed):**

On your Raspberry Pi, if you see `git: command not found` when trying to clone:
```bash
sudo apt update
sudo apt install -y git
```

**Clone the repository:**
```bash
git clone https://github.com/roanvtkc/simpsons-house.git
cd simpsons-house
```

**Run the automated setup:**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- ✅ Install all required packages (including git if missing)
- ✅ Configure MQTT with WebSocket support (ports 1883 and 9001)
- ✅ Set up Python environment and GPIO control
- ✅ Create systemd services for automatic startup
- ✅ Configure mDNS for device discovery
- ✅ Test all components

### 3. iOS App Setup

1. **Open Swift Playgrounds** on your iOS device
2. **Create a new playground** or import the provided Swift package
3. **Copy the Simpson's House app code** into your playground
4. **Update the IP address** if needed (the app defaults to `192.168.5.115`)
5. **Run the app** and grant Local Network permissions when prompted

## 🎮 Using the App

### Connection
1. **Tap "Connect to House"** to establish MQTT over WebSocket connection
2. **Wait for "🏠 Simpson's House Connected!"** status
3. **Start controlling your devices!**

### Device Controls
- **💡 Living Room Light**: Toggle the main lighting
- **🌀 Ceiling Fan**: Control climate systems  
- **🚪 Front Door**: Operate the servo-controlled entrance

### Features
- **📊 Real-time status**: See device states instantly
- **📋 Activity logs**: Monitor all commands and responses
- **ℹ️ System info**: View hardware and network configuration
- **🔄 Auto-reconnect**: Automatic connection recovery

## 🛠️ Configuration

### MQTT Topics
| Topic | Description | Commands |
|-------|-------------|----------|
| `home/light` | Living room light control | `ON`, `OFF` |
| `home/fan` | Ceiling fan control | `ON`, `OFF` |
| `home/door` | Front door servo | `ON` (open), `OFF` (close) |

### Network Ports
- **1883**: MQTT TCP (standard MQTT clients)
- **9001**: MQTT WebSocket (iOS app)

### Service Management
```bash
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
mosquitto_sub -h localhost -t home/# -v
```

## 🔧 Advanced Configuration

### Custom GPIO Pins
Edit `mqttlistener.py` to change pin assignments:
```python
# GPIO pin assignments (BCM numbering)
LIGHT_PIN = 17  # Change to your preferred pin
FAN_PIN   = 27  # Change to your preferred pin  
SERVO_PIN = 22  # Change to your preferred pin
```

### Network Settings
Update the iOS app host address:
```swift
@StateObject private var mqttClient = SimpsonsHouseMQTTClient(host: "YOUR_PI_IP_ADDRESS")
```

### FortiGate Environments
If you're in a corporate environment with FortiGate firewalls:
- The setup script will prompt for certificate installation
- Choose 'y' if you need certificate inspection bypass
- Choose 'n' for home networks

## 🧪 Testing & Verification

### Verify Services
```bash
# Check MQTT broker
sudo systemctl status mosquitto

# Check listening ports (should show both 1883 and 9001)
sudo netstat -tlnp | grep -E "(1883|9001)"

# Test MQTT broker
mosquitto_pub -h localhost -t test/message -m "Hello Simpson's House"
mosquitto_sub -h localhost -t test/# -v

# Check mDNS discovery
avahi-browse -rt _mqtt._tcp
```

### Test GPIO Control
```bash
# Test individual devices
mosquitto_pub -h localhost -t home/light -m ON
mosquitto_pub -h localhost -t home/fan -m OFF
mosquitto_pub -h localhost -t home/door -m ON
```

### Test WebSocket Connection
You can test the WebSocket from a browser:
```javascript
// Open browser console and test WebSocket
const ws = new WebSocket('ws://192.168.5.115:9001');
ws.onopen = () => console.log('WebSocket connected!');
ws.onerror = (error) => console.log('WebSocket error:', error);
```

## 🐛 Troubleshooting

<details>
<summary><strong>Setup Issues</strong></summary>

**"git: command not found" error:**
```bash
sudo apt update
sudo apt install -y git
```
Then retry the git clone command.

**"Permission denied" when running setup:**
```bash
chmod +x setup.sh
./setup.sh
```
Make sure you're running as the `pi` user, not root.
</details>

<details>
<summary><strong>Connection Issues</strong></summary>

**"Connection timeout" in iOS app:**
- Verify both devices are on the same WiFi network
- Check Pi IP address: `hostname -I`
- Test WebSocket manually: Use browser to visit `ws://PI_IP:9001`

**"Service failed to start":**
```bash
# Check service logs
sudo journalctl -u simpsons-house -n 50
sudo journalctl -u mosquitto -n 50

# Restart services
sudo systemctl restart mosquitto
sudo systemctl restart simpsons-house
```
</details>

<details>
<summary><strong>WebSocket Issues</strong></summary>

**"WebSocket connection refused":**
- Verify Mosquitto WebSocket port: `sudo netstat -tlnp | grep 9001`
- Check Mosquitto config: `cat /etc/mosquitto/conf.d/01-simpsons-house.conf`
- Test from command line: `mosquitto_pub -h localhost -t test -m hello`
</details>

<details>
<summary><strong>GPIO Issues</strong></summary>

**"GPIO permissions denied":**
- Ensure the script runs as `pi` user (not root)
- Verify user is in `gpio` group: `groups pi`
- Check systemd service user: `sudo systemctl show simpsons-house | grep User`
</details>

<details>
<summary><strong>Network Discovery Issues</strong></summary>

**"mDNS discovery not working":**
- Check Avahi: `sudo systemctl status avahi-daemon`
- Enable Local Network in iOS Settings → Privacy → Local Network
- Add `_mqtt._tcp` service in Swift Playgrounds capabilities
</details>

### Log Locations
- **Setup logs**: `/tmp/simpsons_house_setup.log`
- **MQTT listener**: `sudo journalctl -u simpsons-house -f`
- **Mosquitto broker**: `/var/log/mosquitto/mosquitto.log`
- **System logs**: `sudo journalctl -f`

### Debug Commands
```bash
# Check all Simpson's House processes
ps aux | grep -E "(mosquitto|mqtt|python)"

# Check network connectivity
ping 192.168.5.115  # From iOS device to Pi

# Verify WebSocket listener
telnet 192.168.5.115 9001

# Monitor GPIO states (if gpio-utils installed)
gpio readall
```

## 🔒 Security Considerations

> ⚠️ **Important**: This project uses `allow_anonymous true` for simplicity. For production use:

- Enable MQTT authentication with username/password
- Use TLS/SSL encryption for MQTT connections
- Configure firewall rules to limit access
- Regular security updates for all components
- Consider VPN access for remote control

## 📱 Swift Playgrounds Configuration

### Required Info.plist entries:
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>Needs local network access to connect to MQTT broker</string>
<key>NSBonjourServices</key>
<array>
    <string>_mqtt._tcp</string>
</array>
```

### App Capabilities:
- **Local Network**: Enable in Settings → Privacy → Local Network
- **Swift Playgrounds**: Allow in Local Network settings
- **Background App Refresh**: Enable for persistent connections

## 📁 Project Structure

```
simpsons-house/
├── 📄 README.md                    # This file
├── 🔧 setup.sh                     # Automated setup script
├── 🐍 mqttlistener.py               # Python MQTT listener
├── 🔐 install_ca.sh                # FortiGate certificate installer
├── 📱 ios-app/                     # Swift Playgrounds app code
│   └── ContentView.swift
├── 📋 systemd/                     # Systemd service files
│   └── simpsons-house.service
└── 📊 docs/                        # Additional documentation
    ├── hardware-setup.md
    ├── troubleshooting.md
    └── api-reference.md
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Code Style
- **Python**: Follow PEP 8 guidelines
- **Swift**: Follow Swift API Design Guidelines
- **Bash**: Use shellcheck for script validation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Roadmap

### Upcoming Features
- [ ] **Temperature sensors** and climate control
- [ ] **Motion detection** and security features
- [ ] **Voice control** integration (Siri Shortcuts)
- [ ] **Web dashboard** for browser control
- [ ] **Schedule automation** and timers
- [ ] **Energy monitoring** and usage statistics
- [ ] **Multiple room support** with zone control
- [ ] **Camera integration** for security monitoring

### Version History
- **v3.0** - MQTT over WebSocket support, systemd integration
- **v2.0** - Basic MQTT control with GPIO
- **v1.0** - Initial HTTP-based control system

## 📞 Support

### Getting Help
- 📖 Check the [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/roanvtkc/simpsons-house/issues)
- 💬 [Discussions](https://github.com/roanvtkc/simpsons-house/discussions)
- ❓ [FAQ](docs/faq.md)

### Community
- 🌟 **Star this repo** if you find it useful!
- 🐦 Follow updates on Twitter: [@SimpsonsHousePi](https://twitter.com/simpsonshousepi)
- 💡 Share your builds and modifications

## 🏠 About Simpson's House

This project brings the iconic Simpson family home into the smart home era! Control Marge's kitchen lights, Homer's ceiling fan, and the front door security - all from your iPhone or iPad using cutting-edge WebSocket technology.

> *"Woo-hoo! Smart home automation!"* - Homer Simpson (probably)

### Technical Innovation
- **MQTT over WebSocket**: First-class iOS support without native MQTT libraries
- **Real-time GPIO control**: Sub-second response times
- **Robust error handling**: Graceful degradation and recovery
- **Professional deployment**: systemd services and proper logging

### Inspiration
Inspired by the beloved animated series "The Simpsons" and the desire to make home automation accessible to everyone, from beginners to advanced makers.

---

**Made with ❤️ for smart home enthusiasts and Simpsons fans**

For support and questions, please [open an issue](https://github.com/roanvtkc/simpsons-house/issues) or check our [troubleshooting guide](docs/troubleshooting.md).

[![GitHub stars](https://img.shields.io/github/stars/roanvtkc/simpsons-house?style=social)](https://github.com/roanvtkc/simpsons-house/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/roanvtkc/simpsons-house?style=social)](https://github.com/roanvtkc/simpsons-house/network/members)
[![GitHub issues](https://img.shields.io/github/issues/roanvtkc/simpsons-house)](https://github.com/roanvtkc/simpsons-house/issues)
[![GitHub license](https://img.shields.io/github/license/roanvtkc/simpsons-house)](https://github.com/roanvtkc/simpsons-house/blob/main/LICENSE)
