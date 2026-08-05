# Teaching Guide — Simpson's House Smart Home

This guide is for teachers and students. It explains what every part of the project does, how the pieces connect, and what to look at when you want to change something.

---

## Quick mental model

Before diving into files, read this once:

```
You tap a button on the iPad
        ↓
The iPad app creates a tiny MQTT message ("ON")
        ↓
The message travels over WiFi to the Raspberry Pi
        ↓
The Mosquitto broker (a small program on the Pi) receives it
        ↓
mqttlistener.py (our Python script) receives it from the broker
        ↓
The Python script sends a HIGH/LOW signal to a GPIO pin
        ↓
The GPIO pin sends electricity to the real hardware
        ↓
The LED turns on / the motor spins / the servo moves
        ↓
The Python script publishes a status message back ("ON")
        ↓
The iPad app receives it and updates the button on screen
```

That whole loop takes less than a second.

---

## Part 1 — The Frontend (iPad App)

The iOS app is written in **SwiftUI** and lives in `SimpsonsHouse.swiftpm.zip`. Unzip it to see all the files. Here is what each one does.

### `MyApp.swift` — App entry point

This is the first file Swift runs when the app starts. It just tells SwiftUI "use `ContentView` as the starting screen." You almost never need to change this.

```swift
@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

**Teaching point:** The `@main` attribute marks the starting point of the whole program.

---

### `Models.swift` — Data that the UI watches

This file defines the data structures the app tracks. The key one is `DeviceStates`:

```swift
class DeviceStates: ObservableObject {
    @Published var lightOn    = false
    @Published var garageOpen = false
    @Published var doorOpen   = false
}
```

**Teaching point:** `@Published` is SwiftUI's magic word. When a `@Published` value changes, every view that uses it automatically redraws. It is how the button on screen changes from "ON" to "OFF" the moment the Pi replies.

---

### `MQTTClient.swift` — The networking engine

This is the most complex file. Students generally do NOT need to change it, but understanding it is valuable. It does three jobs:

**Job 1 — Connect to the Pi over WebSocket**

```swift
func connect() {
    let wsURL = URL(string: "ws://192.168.5.123:9001")
    webSocketTask = urlSession?.webSocketTask(with: request)
    webSocketTask?.resume()
}
```

WebSocket is a way of keeping a persistent two-way connection open. Port 9001 is where Mosquitto listens for WebSocket connections (as opposed to port 1883, which is raw TCP MQTT).

**Job 2 — Send MQTT packets manually**

MQTT has its own binary message format. The app builds these byte-by-byte:

```swift
private func createMQTTPublishPacket(topic: String, message: String) -> Data {
    var packet = Data()
    packet.append(0x30)   // ← first byte: "this is a PUBLISH packet"
    // ... more bytes follow (topic name, message, lengths)
}
```

Teaching point: Network protocols are just agreed formats for bytes. The Pi's Mosquitto broker expects bytes in this exact order — the code is doing exactly what the MQTT specification says.

**Job 3 — Call the right function when a reply arrives**

```swift
private func handleMQTTData(_ data: Data) {
    let messageType = (data[0] >> 4) & 0x0F
    switch messageType {
    case 2:  // CONNACK — broker confirmed our connection
    case 3:  // PUBLISH — a status update from the Pi
    case 13: // PINGRESP — Pi replied to our keep-alive ping
    }
}
```

Teaching point: `>>` is a bit-shift. The first byte of every MQTT packet encodes the message type in its top 4 bits. Shifting right by 4 extracts those bits.

---

### `ContentView.swift` — The screen layout

This is the root view — the "frame" that holds everything else together. Students can safely read and modify this file.

```swift
VStack(spacing: 24) {
    HeroSectionView()            // Title banner at the top
    ConnectionStatusCard(...)    // Shows Connected/Disconnected
    if mqttClient.isConnected {
        DeviceControlsSection(...)  // Buttons for each device
    } else {
        ConnectionPromptView()      // "Tap to Connect" message
    }
}
```

**Teaching point:** The `if mqttClient.isConnected` block is reactive — when `isConnected` changes (because the Pi replied), SwiftUI automatically swaps between showing the controls or the prompt. You did not have to write any "show this, hide that" code.

**Where students can experiment:**
- Change `spacing: 24` to see the sections move closer/further apart
- Add `HeroSectionView()` twice to see it appear twice (then remove the duplicate)
- Change `.background(Color(.systemBackground))` to `.background(Color.yellow.opacity(0.1))` for a yellow tint

---

### `HeroSectionView.swift` — Title banner

The decorative header at the top of the screen. It is completely safe to customise.

**Where students can experiment:**
- Change the title text or emoji
- Change the subtitle text
- Adjust colours and font sizes

---

### `ConnectionStatusCard.swift` — Connection indicator

Shows whether the app is talking to the Pi. Displays the status string from `mqttClient.connectionStatus` and has buttons to open the Logs and Info sheets.

**Teaching point:** Notice it takes `mqttClient` as a parameter. This means it does not own the data — `ContentView` owns it and shares it downward. This is called "dependency injection."

---

### `ConnectionPromptView.swift` — Offline state

A simple view shown when not connected. Has one button:

```swift
Button("Connect to House") {
    mqttClient.connect()
}
```

**Teaching point:** The button calls a function on the MQTT client. Students often ask "but how does it know what mqttClient is?" — it comes in through a `@Binding` or as an `ObservableObject` passed from the parent view.

---

### `DeviceControlsSection.swift` — The grid of device tiles

Arranges the three device cards in a layout:

```swift
LazyVGrid(columns: [...]) {
    DeviceCard(...)       // Living Room Light
    GarageDoorCard(...)   // Garage Door
    DeviceCard(...)       // Front Door
}
```

**Where students can experiment:**
- Add another `DeviceCard` row for a hypothetical new device
- Change the grid column count to make it 1 column or 3 columns

---

### `DeviceCard.swift` — Reusable device tile

A single on/off toggle card used for the light and the front door.

Key parts:
```swift
Button(action: { onToggle() }) {
    VStack {
        Image(systemName: icon)   // SF Symbol icon
        Text(title)
        Text(isOn ? "ON" : "OFF")
    }
}
.background(isOn ? Color.yellow : Color.gray)
```

**Teaching point:** `onToggle` is a **closure** (a function passed as a value). The card does not know what toggling means — the parent decides and passes the behaviour in. This makes the card reusable for any device.

---

### `GarageDoorCard.swift` — Garage-specific tile

Similar to `DeviceCard` but has separate OPEN and CLOSE buttons instead of a toggle, because sending OPEN when it's already open is a meaningful command (the motor needs a direction).

---

### `LogsView.swift` — Activity log sheet

Shows a scrollable list of everything that has happened: commands sent, replies received, errors. Very useful for debugging when the hardware is not responding.

---

### `InfoView.swift` — System info sheet

Shows the IP address, port, topic names, and other configuration. A handy reference without opening the code.

---

### `DebugConnectionView.swift` — Developer debugging tool

A panel used during development. Has a "Force Connection Fix" button that manually sets `isConnected = true` — useful when diagnosing connection state bugs. Not something students normally need.

---

## Part 2 — The Backend (Raspberry Pi Python)

All the backend code lives in `mqttlistener.py`. It is divided into numbered sections (see the comments in the file). Here is the plain-English summary.

### Section 1: Configuration

All the settings — which GPIO pins are used, the MQTT broker address, the topic names — are defined at the top as constants. This means students only need to change one place if the hardware is rewired.

```python
LIGHT_PIN        = 17
GARAGE_SERVO_PIN = 27
SERVO_PIN        = 23
BROKER_HOST      = "localhost"
BROKER_PORT      = 1883
```

---

### Section 2: Logging

Uses Python's `logging` library instead of `print()` so every message gets a timestamp and severity level:

```
2026-04-17 09:12:03 [INFO] Simpson's House: 💡 Living Room Light → ON
```

This makes it much easier to read the terminal output and understand the timeline of events.

---

### Section 3: GPIO Setup (`setup_gpio`)

Runs once at startup. Tells the Raspberry Pi:
- Which numbering scheme to use (BCM — matches the numbers on the pinout diagram)
- Which pins are outputs (driving components) vs inputs (reading sensors)
- Initial states (everything starts OFF)
- Sets up 50 Hz PWM on both servo pins

---

### Section 4: Servo Control (`set_servo_angle`)

Both doors are driven by **SG90 hobby servos** — the garage door on GPIO 27, the
front door on GPIO 23. Neither needs a driver board.

**Why no driver board?**
A servo has its own motor, gearbox and control circuit inside. The Pi only sends
it a low-current *signal*; the servo does the work. The 5V pin supplies enough
current for an SG90 directly.

**How the servo knows where to go:**
The Pi sends a 50 Hz pulse train. The *width* of each pulse tells the servo the
angle. The servo compares that against its internal position sensor and drives
its motor until they match, then holds.

```python
duty = (angle / 180.0) * 10 + 2   # 0° → 2%, 180° → 12%
pwm.ChangeDutyCycle(duty)
time.sleep(0.8)                    # give the servo time to travel
pwm.ChangeDutyCycle(0)             # stop pulsing so it doesn't hum
```

One function serves both doors — you pass in the PWM object for whichever servo
you want to move. `control_garage_door()` and `control_door()` both map
**open = 90°, closed = 0°**. Change those angles to match how you physically
mount the servo horn.

**Teaching point:** this is the difference between *open-loop* and *closed-loop*
control. A stepper (the old design) is open-loop — you count steps and hope. A
servo is closed-loop — it measures its own position and corrects itself.

---

### Section 5: MQTT Event Handlers

Three functions the MQTT library calls automatically:

| Function | When it's called | What it does |
|---|---|---|
| `on_connect` | When connected to Mosquitto | Subscribes to all three topics, publishes initial device states |
| `on_disconnect` | When connection drops | Logs the event |
| `on_message` | When a message arrives | Decodes it, validates it, calls the device function, publishes status back |

`on_message` is the most important. The decision flow is:

```
Message arrives on "home/light"
    → Is it "ON" or "OFF"?
        → Yes → call control_light(True/False)
        → No  → publish error, ignore message
```

---

### Section 6: Device Control Functions

| Function | Hardware it controls | How |
|---|---|---|
| `control_light(state)` | LED on GPIO 17 | Sets pin HIGH or LOW |
| `control_garage_door(open_door)` | Servo motor on GPIO 27 | Calls `set_servo_angle(GARAGE_SERVO_PWM, 90 or 0)` |
| `control_door(state)` | Servo motor on GPIO 23 | Calls `set_servo_angle(SERVO_PWM, 90 or 0)` |

Both call the same `set_servo_angle()` helper — only the PWM object differs.

---

### Section 7: Shutdown

- `cleanup_and_exit()` — stops both PWM channels and releases the GPIO pins
- Runs from the `finally` block in `main()`, so it executes even on a crash
- The MQTT "last will" message also tells the app the controller went offline

---

### Section 8: MQTT Publishing

After carrying out a command, the Pi sends a status update back to the app:

| Topic | What it contains | Example value |
|---|---|---|
| `home/light/status` | Plain text | `ON` |
| `home/garage/status` | Plain text | `OPEN` |
| `home/door/status` | Plain text | `ON` |
| `home/garage/motor_status` | JSON | `{"running": false, "position": 100}` |
| `home/status` | JSON | All device states + timestamp |
| `home/system` | JSON | Version, GPIO pin layout |

`retain=True` means Mosquitto remembers the last message. When the app reconnects it immediately gets the current state.

---

### Section 9–11: Utilities, Shutdown, and Main

- **Signal handling** — catches Ctrl+C (`SIGINT`) and `systemd stop` (`SIGTERM`) to shut down cleanly
- **`cleanup_and_exit`** — stops the motor, turns off LEDs, releases GPIO, disconnects from MQTT
- **`main`** — the entry point: initialises GPIO, creates the MQTT client, connects, then runs forever processing messages

---

## Part 3 — The Infrastructure (Mosquitto Broker)

Mosquitto is a small program that runs on the Pi in the background. Students don't write code for it, but understanding its role is important.

**What it does:** Receives messages from publishers, routes them to subscribers on the same topic.

```
iPad publishes → home/light → "ON"
                      ↓
              Mosquitto broker
                      ↓
mqttlistener.py subscribed to home/light receives "ON"
```

**Two ports:**
- **1883** — raw MQTT (used by command-line tools like `mosquitto_pub`)
- **9001** — MQTT over WebSocket (used by the iPad app)

**Useful commands to run on the Pi:**

```bash
# Watch all messages in real time
mosquitto_sub -h localhost -t home/# -v

# Manually send a command (useful for testing without the iPad)
mosquitto_pub -h localhost -t home/light -m ON
mosquitto_pub -h localhost -t home/garage -m OPEN
mosquitto_pub -h localhost -t home/door -m ON

# Check the broker is running
sudo systemctl status mosquitto
```

---

## Part 4 — Step-by-step: what happens when you tap "Light ON"

1. **DeviceCard.swift** — `onToggle()` closure is called
2. **MQTTClient.swift** `toggleLight()` — flips `deviceStates.lightOn` to `true`, calls `publishCommand(topic: "home/light", command: "ON")`
3. **MQTTClient.swift** `publishCommand` — calls `createMQTTPublishPacket("home/light", "ON")` to build a 13-byte binary MQTT packet
4. **MQTTClient.swift** — sends the packet over the WebSocket to `ws://192.168.5.123:9001`
5. **Mosquitto** (on Pi) — receives the WebSocket data, unwraps it as an MQTT PUBLISH packet, routes it to all subscribers of `home/light`
6. **mqttlistener.py** `on_message()` — receives the message, decodes payload: `b'ON'` → `"ON"`
7. **mqttlistener.py** `control_light(True)` — runs `GPIO.output(17, GPIO.HIGH)` → 3.3V on pin 17
8. **GPIO 17** → current flows through 220Ω resistor → **LED lights up**
9. **mqttlistener.py** `publish_device_status("light", True)` — publishes `"ON"` to `home/light/status`
10. **Mosquitto** routes the status message back to the app's WebSocket
11. **MQTTClient.swift** `handleMQTTData()` — receives it, logs `"📨 House status update received"`
12. The `@Published var deviceStates` change triggers SwiftUI to redraw the `DeviceCard` → button now shows yellow "ON" state

---

## Part 5 — Student exercises

### Beginner: Customise the app appearance

Open `SimpsonsHouse.swiftpm` in Swift Playgrounds and find:

1. In `HeroSectionView.swift` — change the title emoji and text
2. In `ContentView.swift` — change the background colour
3. In `DeviceCard.swift` — change the "ON" colour from `Color.yellow` to `Color.green`

Run the app and see the changes immediately.

---

### Intermediate: Change how far the garage door opens

On the Raspberry Pi, open `mqttlistener.py`:

```python
GARAGE_TRAVEL_STEPS = 100   # ← change this number
```

Increase it (e.g. 200) and restart the service:

```bash
sudo systemctl restart simpsons-house
```

Send an OPEN command and observe whether the door travels further:

```bash
mosquitto_pub -h localhost -t home/garage -m OPEN
```

Adjust until the travel distance matches your physical model.

---

### Intermediate: Add terminal logging for the servo angle

In `control_door()` in `mqttlistener.py`, the servo angle is calculated as `90 if state else 0`. Change the fully-open angle to 120° and verify you can see the servo move further. Add a log message to print the exact duty cycle being sent.

---

### Advanced: Add a new device

**Step 1 — Backend:** In `mqttlistener.py`:

```python
# Add a new constant
FAN_PIN = 25

# In setup_gpio(), add:
GPIO.setup(FAN_PIN, GPIO.OUT, initial=GPIO.LOW)

# Add a new control function:
def control_fan(state: bool) -> bool:
    GPIO.output(FAN_PIN, GPIO.HIGH if state else GPIO.LOW)
    logger.info(f"🌀 Fan → {'ON' if state else 'OFF'}")
    return True

# In on_connect(), subscribe to the new topic:
client.subscribe("home/fan")

# In on_message(), add a new elif branch:
elif topic == "home/fan":
    valid_commands = {"ON": True, "OFF": False}
    command_state  = valid_commands.get(payload)
    success        = control_fan(command_state)
```

**Step 2 — Frontend:** In `DeviceControlsSection.swift`, add:

```swift
DeviceCard(
    title: "Fan",
    icon: "wind",
    isOn: mqttClient.deviceStates.fanOn,
    onToggle: { mqttClient.toggleFan() }
)
```

Then add `var fanOn = false` to `DeviceStates` in `Models.swift`, and add `toggleFan()` to `MQTTClient.swift` following the same pattern as `toggleLight()`.

---

### Advanced: Monitor all MQTT traffic live

On the Pi, run:

```bash
mosquitto_sub -h localhost -t home/# -v
```

Then use the iPad app to control devices. Observe every message published in both directions in real time. Try to match each line of terminal output to a step in the "Part 4" trace above.

---

## Part 6 — Common questions

**Q: Why does the app use WebSocket (port 9001) instead of direct MQTT (port 1883)?**

iOS does not have a built-in MQTT library. WebSocket is a standard protocol that iOS's `URLSession` supports natively. By telling Mosquitto to accept MQTT packets wrapped in WebSocket frames (on port 9001), we can talk MQTT from any iOS app without third-party libraries.

**Q: Why does each servo need only one GPIO pin?**

Everything the servo needs to know travels on a single signal wire, encoded as the width of a repeating pulse. The servo's own circuit reads that pulse and drives its motor. (The earlier stepper design needed four pins, because the Pi had to energise each of the motor's four coils itself.)

**Q: Why not just use `GPIO.HIGH/LOW` for the servo too?**

Servos need a very precise timing signal (a pulse between 1ms and 2ms wide, repeated 50 times per second) to know their target angle. PWM (Pulse Width Modulation) generates exactly that. GPIO.HIGH/LOW is on/off — no timing information.

**Q: What happens if the Pi crashes while the motor is running?**

The `cleanup_and_exit()` function runs in the `finally` block of `main()`, which Python always executes even on a crash. It stops both PWM channels and releases the GPIO pins before the process exits. The MQTT "last will" message also tells the app the controller went offline.

**Q: Why does `retain=True` matter on status topics?**

Without `retain=True`, if the app connects AFTER the last status was published, it would not know the current state of the devices — it would show everything as OFF even if the light is on. With retain, Mosquitto caches the last message and delivers it immediately to any new subscriber.
