# Simpsons House Control (MQTT)

A simple home‑automation project: control LEDs and a servo on a Raspberry Pi directly from a SwiftUI app using MQTT.

## Table of Contents

* [Features](#features)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Usage](#usage)
* [Verifying Services](#verifying-services)
* [Hardware Wiring](#hardware-wiring)
* [SwiftUI App Configuration](#swiftui-app-configuration)
* [License](#license)

## Features

* **Direct MQTT control**: no HTTP proxy needed, uses Mosquitto broker on the Pi.
* **SwiftUI interface**: built in Swift Playgrounds or Xcode with SwiftMQTT.
* **mDNS discovery**: Avahi advertises `_mqtt._tcp` so iOS devices can find the broker.

## Prerequisites

* Raspberry Pi running Raspberry Pi OS (formerly Raspbian).
* SSH access to the Pi (default `pi`/`tkcraspberry`).
* iPad or macOS device on the same local network.

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/roanvtkc/simpsons-house.git
   cd simpsons-house
   ```
2. **Run the setup script**

   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   This will:

   * Install Mosquitto broker and Avahi for mDNS.
   * Create a Python virtual environment and install required packages (`paho-mqtt`, `RPi.GPIO`).
   * Configure Avahi to advertise the MQTT service on `_mqtt._tcp` port 1883.
   * Launch the MQTT listener script in the background.

## Usage

1. On your iPad/macOS, open the SwiftUI app (`SimpsonsHouse.swiftpm`) in Swift Playgrounds or Xcode.
2. Grant **Local Network** permission when prompted.
3. Tap the toggles to send MQTT messages to the Pi and control the hardware.

## Verifying Services

* **Mosquitto broker**:

  ```bash
  sudo systemctl status mosquitto
  ```
* **mDNS advertisement**:

  ```bash
  avahi-browse -rt _mqtt._tcp
  ```
* **Listener logs**:

  ```bash
  tail -f /tmp/mqttlistener.log
  ```

## Hardware Wiring

Use BCM pin numbers:

|     Device | BCM Pin | Notes                                       |
| ---------: | ------: | ------------------------------------------- |
|  Light LED |      17 | LED + 220 Ω resistor to GND                 |
|    Fan LED |      27 | LED or small fan (use transistor if needed) |
| Door Servo |      22 | Servo signal to pin, power to 5 V + GND     |

Ensure external loads are driven via appropriate drivers or relays.

## SwiftUI App Configuration

* **Swift Package**: includes `SwiftMQTT` dependency.
* **Info.plist** entries:

  ```xml
  <key>NSLocalNetworkUsageDescription</key>
  <string>Needs local network access to connect to MQTT broker</string>
  <key>NSBonjourServices</key>
  <array>
    <string>_mqtt._tcp</string>
  </array>
  ```
* **Host IP fallback**: you can hard‑code your Pi’s IP in `ContentView.swift` if mDNS fails.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
