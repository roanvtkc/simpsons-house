# Simpsons House Control (MQTT)

A simple home‑automation project: control LEDs and a servo on a Raspberry Pi directly from a SwiftUI app using MQTT.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Verifying Services](#verifying-services)
- [Hardware Wiring](#hardware-wiring)
- [SwiftUI App Configuration](#swiftui-app-configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Direct MQTT control**: no HTTP proxy needed; uses Mosquitto broker on the Pi.
- **SwiftUI interface**: buildable in Swift Playgrounds or Xcode with SwiftMQTT.
- **mDNS discovery**: Avahi advertises `_mqtt._tcp` so iOS devices can find the broker automatically.

## Prerequisites

- **Raspberry Pi** running Raspberry Pi OS (32‑ or 64‑bit).
- **SSH access** to the Pi (default credentials: `pi`/`tkcraspberry`).
- **iPadOS 15+ or macOS** device on the same local network.
- **Swift Playgrounds 4** or **Xcode 13+** for the SwiftUI app.

## Installation

1. **Install Git (if needed)**
   
   On your Raspberry Pi, if you see `git: command not found` when cloning:
   ```bash
   sudo apt update
   sudo apt install -y git
   ```

2. **Clone the repository** (on your development machine or Pi):
   ```bash
   git clone https://github.com/roanvtkc/simpsons-house.git
   cd simpsons-house
   ```

3. **Run the setup script** (installs dependencies and starts services):
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   This will:
   - Install system packages: `git`, `python3-venv`, `mosquitto`, `avahi-daemon`, and `build-essential`.
   - Create a Python virtual environment and install `paho-mqtt` and `RPi.GPIO`.
   - Configure Avahi to advertise the MQTT service on `_mqtt._tcp` port 1883.
   - Start the Mosquitto broker and the `mqttlistener.py` script in the background.
   - Configure Mosquitto to listen on all interfaces via /etc/mosquitto/conf.d/01-listener.conf
     with the following contents:
     ```conf
     listener 1883 0.0.0.0
     allow_anonymous true
     ```
     Restart the service with `sudo systemctl restart mosquitto`.

## Usage

1. **Open the SwiftUI app**
   - On iPad: open `SimpsonsHouse.swiftpm` in Swift Playgrounds.
   - On macOS: open the Swift package in Xcode.
2. **Grant Local Network permission** when prompted.
3. **Toggle controls** in the UI to send MQTT messages and control the Pi hardware.

## Verifying Services

- **Mosquitto broker**:
  ```bash
  sudo systemctl status mosquitto
  ```
- **Listener check**:
  ```bash
  sudo netstat -tlnp | grep 1883
  ```
  You should see `0.0.0.0:1883` (and `:::1883`) rather than `127.0.0.1:1883`.
- **Broker test**:
  ```bash
  mosquitto_pub -h localhost -t home/light -m ON
  mosquitto_sub -h localhost -t home/# -v
  ```
  You should see the `home/light` message printed.
- **mDNS advertisement**:
  ```bash
  avahi-browse -rt _mqtt._tcp
  ```
- **Listener logs**:
  ```bash
  tail -f /tmp/mqttlistener.log
  ```

## Hardware Wiring

Use BCM pin numbering:

| Device     | BCM Pin | Notes                                          |
|-----------:|--------:|------------------------------------------------|
| Light LED  |      17 | LED + 220 Ω resistor to GND                   |
| Fan LED    |      27 | LED or small fan (use transistor if needed)   |
| Door Servo |      22 | Servo signal to pin; power from 5 V and GND   |

> ⚠️ Use appropriate drivers or relays for high‑current loads.

## SwiftUI App Configuration

- **Swift Package Manager** dependency:
  ```swift
  .package(url: "https://github.com/aciidgh/SwiftMQTT.git", from: "3.0.0")
  ```
- **Info.plist** entries:
  ```xml
  <key>NSLocalNetworkUsageDescription</key>
  <string>Needs local network access to connect to MQTT broker</string>
  <key>NSBonjourServices</key>
  <array>
    <string>_mqtt._tcp</string>
  </array>
  ```
- **Host IP fallback**: you may hard‑code your Pi’s IP in `ContentView.swift` if mDNS discovery fails.
- **Swift Playgrounds capability**: In App Settings → Capabilities → Local Network, add the service `_mqtt._tcp` and ensure Playgrounds is allowed in Settings → Privacy → Local Network.

## Troubleshooting

### Git not found on Pi

If you run `git clone` and see `git: command not found`, install Git manually:
```bash
sudo apt update
sudo apt install -y git
```  
Then retry `git clone`.

### SSH host key changed

On your client (macOS/iPad SSH app), clear the old key:
```bash
ssh-keygen -R <pi_ip_address>
```  
Or remove the offending line in `~/.ssh/known_hosts` manually.

### MQTT connection errors

- Verify the broker is listening: `sudo netstat -tlnp | grep 1883` (should show `0.0.0.0:1883`).
- Test publish/subscription locally as in the *Verifying Services* section.
- Check Avahi advertisement: `avahi-browse -rt _mqtt._tcp`.
- Ensure Playgrounds is allowed under Settings → Privacy → Local Network.
- If problems persist, add this Swift snippet before connecting:
  ```swift
  let testConn = NWConnection(host: .init("<pi_ip>"), port: 1883, using: .tcp)
  testConn.stateUpdateHandler = { print("Socket test state:", $0) }
  testConn.start(queue: .main)
  ```
  A state of `.ready` means the connection path is open.

## License

This project is licensed under MIT. See [LICENSE](LICENSE) for details.
