# Simpsons House Control

This project provides a simple SwiftUI interface for toggling devices in a simulated "Simpsons" house. The app communicates with a Python MQTT bridge running on a Raspberry Pi to control GPIO pins.

## Components

- **SimpsonsHouse.swift** – SwiftUI interface that sends HTTP POST requests to the MQTT bridge.
- **mqttbridge.py** – Flask service that receives HTTP requests and publishes MQTT messages.
- **mqttlistener.py** – MQTT client meant to run on the Raspberry Pi. It listens for MQTT topics and sets GPIO states:
  - `light` and `fan` topics toggle digital output pins.
  - `door` topic controls a servo between 0° and 90°.
- **simpsonsHouse/** – Swift Package containing the SwiftUI code. `Info.plist` has been added to allow HTTP communication on the local network.
- The Swift package previously included a playground thumbnail and ZIP archive which were removed to keep the repository free of binary files.

## Usage

1. Install Python dependencies on the Raspberry Pi:
   ```bash
   pip install flask paho-mqtt RPi.GPIO
   ```
2. Run the MQTT bridge:
   ```bash
   python mqttbridge.py
   ```
3. In another terminal on the Pi, run the listener:
   ```bash
   sudo python mqttlistener.py
   ```
4. Build and run the Swift package on your iOS device or simulator.

## Allowing HTTP Requests on iOS

`Info.plist` includes the `NSAllowsArbitraryLoads` setting, which disables App Transport Security restrictions so the app can communicate with the local HTTP bridge.
