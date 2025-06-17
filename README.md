# Simpsons House Control

This project provides a simple SwiftUI interface for toggling devices in a simulated "Simpsons" house. The app communicates with a Python MQTT bridge running on a Raspberry Pi to control GPIO pins.

## Components

- **mqttbridge.py** – Flask service that receives HTTP requests and publishes MQTT messages.
- **mqttlistener.py** – MQTT client meant to run on the Raspberry Pi. It listens for MQTT topics and sets GPIO states:
  - `light` and `fan` topics toggle digital output pins.
  - `door` topic controls a servo between 0° and 90°.
- **SimpsonsHouse.swiftpm.zip** – Swift package containing the SwiftUI interface. Unzip this archive and open the `SimpsonsHouse.swiftpm` folder in Swift Playgrounds. The Local Network capability is declared in `Package.swift`.
- The package is stored as a ZIP file so you can easily open it on an iPad.

## Usage

1. **Connect to your Raspberry Pi via SSH**. An easy way on iPad is the free
   **Shelly** app from the App Store.
   - Add a new host in Shelly using the Pi's IP address (found via your router or
     by running `hostname -I` directly on the Pi).
   - When prompted, log in with **username** `pi` and **password**
     `tkcraspberry`.

2. **Download this repository onto the Pi** so the bridge and listener scripts
   are available. If Git is not installed, you can install it first. The
   repository is public, so cloning is straightforward:
   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/roanvtkc/simpsons-house.git
   cd simpsons-house
   ```
   If you ever work from a private fork you'll need to authenticate using a
   personal access token or SSH key. You can also download a ZIP file instead,
   as described in the **Opening on an iPad** section.

3. **Run the setup script** to install dependencies and launch the Python services:
   ```bash
   ./setup.sh
   ```
   The script installs required packages, sets up a Python virtual environment,
   starts the Mosquitto broker, and runs both the bridge and listener in the
   background.

4. **Build and run the Swift package** on your iOS device or simulator.

## Allowing HTTP Requests on iOS

`Package.swift` enables the Local Network capability and lists the `_http._tcp` Bonjour service so the app can communicate with the HTTP bridge on your network.

## Advertising the HTTP service via Bonjour

Swift Playgrounds only allows network access to hosts it discovers through Bonjour with service types that match your package's capabilities. Run an mDNS advertiser on the Raspberry Pi so Playgrounds detects the bridge automatically.

1. **Install Avahi**
   ```bash
   sudo apt-get update
   sudo apt-get install avahi-daemon avahi-utils
   ```
2. **Create a service definition**
   1. Make sure the services folder exists:
      ```bash
      sudo mkdir -p /etc/avahi/services
      ```
   2. Open a new file with `nano`:
      ```bash
      sudo nano /etc/avahi/services/mqtt-http.service
      ```
      Paste the following text, then press <kbd>Ctrl</kbd>+<kbd>X</kbd>, choose
      **Y** for yes and hit <kbd>Enter</kbd> to save:
      ```xml
      <?xml version="1.0" standalone='no'?>
      <!DOCTYPE service-group SYSTEM "avahi-service.dtd">
      <service-group>
        <name replace-wildcards="yes">Simpsons House MQTT</name>
        <service>
          <type>_http._tcp</type>
          <port>5000</port>
        </service>
      </service-group>
      ```
3. **Restart Avahi**
   ```bash
   sudo systemctl restart avahi-daemon
   ```
4. **Verify the broadcast** from a macOS terminal:
   ```bash
   dns-sd -B _http._tcp
   ```
   The `Simpsons House MQTT` service should appear in the list.

In Playgrounds, enable Local Network under **Settings → Capabilities**, add `_http._tcp` to the Bonjour section, and resume the live view. When prompted, allow the connection. Playgrounds will now discover the Pi's HTTP service and permit calls to `http://10.20.5.66:5000/send`.

## Enabling Avahi Reflector

Use Avahi's reflector mode when devices on different VLANs need to see each other via Bonjour. These steps assume you are editing on the Raspberry Pi itself.

1. **Open the configuration file**
   ```bash
   sudo nano /etc/avahi/avahi-daemon.conf
   ```

2. **Find or create the `[reflector]` section**
   Add the following lines (remove any `#` at the start if they are commented out):
   ```
   [reflector]
   enable-reflector=yes
   # Optionally limit forwarding to specific VLAN interfaces
   allow-interfaces=eth0.105,eth0.108,eth0.122
   ```
   Exit **nano** by pressing <kbd>Ctrl</kbd>+<kbd>X</kbd>, then **Y** and <kbd>Enter</kbd> to save.

3. **Restart Avahi** so the new settings take effect
   ```bash
   sudo systemctl restart avahi-daemon
   ```

4. **Verify the reflector**
   On a device in another VLAN, run a discovery command such as:
   ```bash
   dns-sd -B _http._tcp
   ```
   If `Simpsons House MQTT` shows up, the reflector is working.

Reflecting mDNS across VLANs can expose services more widely, so enable it only if you understand that risk.


## Opening on an iPad

If you have never used GitHub or Swift Playgrounds before, follow these steps:

1. Visit the repository page in a web browser and tap **Code \> Download ZIP**.
2. Open the downloaded ZIP file in the **Files** app to extract it.
3. Inside the extracted folder you will find **SimpsonsHouse.swiftpm**. Tap this folder and choose **Open in Swift Playgrounds**.
4. Once the project opens you can build and run it directly on your iPad.

### Troubleshooting

If Playgrounds displays an error like "Could not load app target description" it usually means a different folder was opened. Make sure the `.swiftpm` package itself is selected when launching Playgrounds.

### Changing the Raspberry Pi IP

The Swift code sends requests to the Python service running on your Raspberry Pi. To point the app at your own Pi:

1. In Swift Playgrounds, open `ContentView.swift`.
2. Near the top of the file locate the line that looks like:

   ```swift
   guard let url = URL(string: "http://10.20.5.66:5000/send") else { return }
   ```

3. Replace `10.20.5.66` with the IP address of your Pi. You can find the address on the Pi by running `hostname -I` in the terminal.

Save the file and run the project again. The toggles will now send commands to your Pi.

## Hardware wiring

The `mqttlistener.py` script expects the following connections on the Pi (using the BCM pin numbering scheme):

| Device | BCM Pin | Notes |
|-------|--------|------|
| Light output | **17** | Connect an LED (with a 220 Ω resistor) between pin 17 and ground. |
| Fan output | **27** | Connect another LED or small DC fan between pin 27 and ground. |
| Servo | **22** | Connect the servo signal wire to pin 22, power to the Pi's 5 V pin and ground to a ground pin. |

Make sure your components do not draw more current than the Pi can supply directly. When in doubt, use a transistor or relay module to switch larger loads.

