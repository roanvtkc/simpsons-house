# Extension Guide — Adding Your Own Circuits

For students who have the light, garage door and front door working, and want
to add something of their own.

You will add one new device end to end: a physical component on the
breadboard, a control function on the Raspberry Pi, and a button in the iPad
app.

---

## Safety first

- **Low voltage only.** Everything in this project runs on 3.3V or 5V from the
  Pi. Never wire anything to mains power. If your idea needs mains, it does not
  go in this project.
- **Power the Pi off** before adding or moving any wire.
- **Check the current.** A single GPIO pin can supply about 16 mA safely, and
  the whole chip about 50 mA total. An LED is fine. A motor is not — it needs
  its own power supply and a transistor or driver board.
- If anything gets hot or smells, unplug it immediately.

---

## How a device is wired into the software

Every device already in this project exists in **eight places**. Adding one
means repeating that same pattern. Nothing here is clever — it is the same
five lines copied and renamed.

```
   iPad app                                Raspberry Pi
   ─────────                               ────────────
   1. DeviceStates property   ──┐
   2. topics list               │   MQTT     ┌── 5. TOPIC_ constant
   3. toggle function        ───┼──────────▶ ├── 6. device_states entry
   4. card in the grid          │            ├── 7. control function
                                │            └── 8. branch in on_message()
                                │                     │
                                └──── status ◀────────┘
```

Plus one on the hardware side: **the GPIO pin constant**.

---

## Worked example — adding a doorbell buzzer

We will add an active buzzer on **GPIO 5** (physical pin 29), controlled by a
new topic `home/buzzer`.

Pick a different pin if GPIO 5 is already used in your build. Free pins in this
project include 5, 6, 12, 13, 16, 19, 20, 21, 26. Already taken: **17** (light),
**27** (garage servo), **23** (front door servo).

### Step 1 — Wire the buzzer

An **active** buzzer makes a sound whenever it has power. A **passive** buzzer
needs a PWM signal and will stay silent on a plain HIGH — check which one you
have.

```
Pi GPIO 5 (pin 29) ─── Buzzer (+) long leg
                       Buzzer (−) short leg ─── Pi GND (pin 30)
```

Power the Pi back on before continuing.

---

### Step 2 — Python: add the pin

In `mqttlistener.py`, **Section 1: Configuration**, next to the other pins:

```python
LIGHT_PIN        = 17   # Living Room Light
GARAGE_SERVO_PIN = 27   # Garage Door Servo signal wire
SERVO_PIN        = 23   # Front Door Servo signal wire
BUZZER_PIN       = 5    # Doorbell buzzer          <-- NEW
```

### Step 3 — Python: add the topic

A few lines below, with the other topics:

```python
TOPIC_LIGHT  = "home/light"
TOPIC_GARAGE = "home/garage"
TOPIC_DOOR   = "home/door"
TOPIC_BUZZER = "home/buzzer"    # <-- NEW
```

### Step 4 — Python: add it to the state tracker

```python
device_states = {
    "light":  False,
    "garage": False,
    "door":   False,
    "buzzer": False,    # <-- NEW
}
```

> **The key name matters.** `on_message()` works it out from the topic with
> `topic.split('/')[-1]`, so `home/buzzer` becomes `"buzzer"`. The dictionary
> key must match the last word of the topic exactly, or the status update back
> to the iPad will fail.

### Step 5 — Python: set the pin up

In `setup_gpio()`, alongside the other `GPIO.setup()` calls:

```python
GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)    # <-- NEW
```

`initial=GPIO.LOW` means the buzzer starts silent. Without it the pin state is
undefined and your buzzer may shriek the moment the service starts.

### Step 6 — Python: subscribe to the topic

In `on_connect()`, add your topic to the list the Pi listens on:

```python
for topic in [TOPIC_LIGHT, TOPIC_GARAGE, TOPIC_DOOR, TOPIC_BUZZER]:
```

**This is the step people forget.** Miss it and everything else looks correct,
but the Pi never hears the message.

### Step 7 — Python: write the control function

In **Section 5: Device Control Functions**, copy `control_light()` and rename it:

```python
def control_buzzer(state: bool) -> bool:
    """Turn the doorbell buzzer on or off."""
    try:
        GPIO.output(BUZZER_PIN, GPIO.HIGH if state else GPIO.LOW)
        logger.info(f"🔔 Buzzer → {'ON' if state else 'OFF'}")
        return True
    except Exception as e:
        logger.error(f"❌ Buzzer control error: {e}")
        return False
```

### Step 8 — Python: route the message

In `on_message()`, add a branch alongside the others, **before** the final
`else`:

```python
elif topic == TOPIC_BUZZER:
    valid_commands = {"ON": True, "OFF": False}
    device_name    = "Doorbell Buzzer"
    command_state  = valid_commands.get(payload)
    if command_state is None:
        publish_error(topic, f"Invalid command: {payload}. Use ON or OFF.")
        return
    success = control_buzzer(command_state)
```

### Step 9 — Test the Pi on its own

Before touching the app, prove the Python half works. Restart the service and
send a message by hand from a second terminal:

```bash
sudo systemctl restart simpsons-house.service
mosquitto_pub -h localhost -t home/buzzer -m "ON"
mosquitto_pub -h localhost -t home/buzzer -m "OFF"
```

Watch the log while you do it:

```bash
journalctl -u simpsons-house.service -f
```

If the buzzer sounds, the whole Pi side is finished. **Do not move on until
this works** — debugging Python and Swift at the same time is much harder.

---

## Now the iPad app

### Step 10 — Swift: add the state property

Open `Models.swift`. This file is normally marked *do not edit* — adding a
device is the one time you are meant to.

```swift
class DeviceStates: ObservableObject {
    @Published var lightOn = false
    @Published var garageOpen = false
    @Published var doorOpen = false
    @Published var buzzerOn = false    // <-- NEW
}
```

### Step 11 — Swift: add the topic

In `MQTTClient.swift`, in the `topics` list near the top:

```swift
private let topics = [
    "home/light",   // GPIO 17 - Living Room Light
    "home/garage",  // GPIO 27 - Garage Door Servo
    "home/door",    // GPIO 23 - Front Door Servo
    "home/buzzer"   // GPIO 5  - Doorbell Buzzer     <-- NEW
]
```

### Step 12 — Swift: add the toggle function

Under `// MARK: - Device Controls`, copy `toggleLight()`:

```swift
func toggleBuzzer() {
    let newState = !deviceStates.buzzerOn
    deviceStates.buzzerOn = newState
    receivedMessages.append("DEBUG: Buzzer toggled to \(newState ? "ON" : "OFF")")
    publishCommand(topic: "home/buzzer", command: newState ? "ON" : "OFF", device: "Doorbell Buzzer")
}
```

### Step 13 — Swift: handle send failures

Still in `MQTTClient.swift`, inside `publishCommand()`, there is a block that
undoes the toggle if the message could not be sent. Add your device:

```swift
if topic == "home/light" { self?.deviceStates.lightOn.toggle() }
else if topic == "home/garage" { self?.deviceStates.garageOpen.toggle() }
else if topic == "home/door" { self?.deviceStates.doorOpen.toggle() }
else if topic == "home/buzzer" { self?.deviceStates.buzzerOn.toggle() }   // <-- NEW
```

Skip this and the button will lie to you: it will look on while the buzzer is
off.

### Step 14 — Swift: add the card

In `DeviceControlsSection.swift`, inside the `LazyVGrid`:

```swift
DeviceCard(
    icon: "bell.fill",
    title: "Doorbell",
    subtitle: "Buzzer",
    isOn: mqttClient.deviceStates.buzzerOn,
    accentColor: .red,
    action: { mqttClient.toggleBuzzer() }
)
```

`icon` is an SF Symbol name. Browse them in the SF Symbols app, or try
`bell.fill`, `fan.fill`, `drop.fill`, `flame.fill`, `speaker.wave.2.fill`.

### Step 15 — Swift: fix the counter

The badge is hardcoded to three devices. In the same file:

```swift
Text("\(activeDevicesCount)/4 Active")     // was /3
```

and in `activeDevicesCount` below:

```swift
if mqttClient.deviceStates.buzzerOn { count += 1 }    // <-- NEW
```

---

## Checklist

Copy this for each new device you add.

**Raspberry Pi — `mqttlistener.py`**
- [ ] Pin constant in Section 1
- [ ] `TOPIC_` constant in Section 1
- [ ] Key in `device_states` (must match the last word of the topic)
- [ ] `GPIO.setup()` in `setup_gpio()`
- [ ] Topic added to the subscribe list in `on_connect()`
- [ ] `control_yourdevice()` function in Section 5
- [ ] `elif` branch in `on_message()`
- [ ] Tested with `mosquitto_pub`

**iPad app**
- [ ] `@Published` property in `Models.swift`
- [ ] Topic in the `topics` list in `MQTTClient.swift`
- [ ] `toggleYourDevice()` function
- [ ] Revert line in `publishCommand()`
- [ ] `DeviceCard` in `DeviceControlsSection.swift`
- [ ] Badge count and `activeDevicesCount` updated

---

## Harder extensions

**A device with a range, not just on/off.** A brightness-controlled LED or a
third servo needs a number, not `ON`/`OFF`. Send the number as the payload
(`mosquitto_pub -t home/lamp -m "75"`) and parse it:

```python
elif topic == TOPIC_LAMP:
    try:
        level = int(payload)
    except ValueError:
        publish_error(topic, f"Invalid level: {payload}. Use 0-100.")
        return
    if not 0 <= level <= 100:
        publish_error(topic, "Level must be 0-100.")
        return
    success = control_lamp(level)
```

In the app, a `Slider` replaces the button. You will need your own card rather
than `DeviceCard`, which only understands on/off — copy `GarageDoorCard.swift`,
which is already a custom card, as your starting point.

**A sensor instead of an output.** A PIR motion sensor or button reads *into*
the Pi (`GPIO.setup(PIN, GPIO.IN)`), then publishes a message rather than
receiving one. Look at `publish_device_status()` in Section 6 for how to send
data up to the app, and set the card's `action` to do nothing.

**Ideas worth trying:** porch light on a second LED, a fan using a transistor,
an RGB LED using three PWM pins, a reed switch that detects when the front door
is actually shut, a temperature sensor on the roof.

---

## When it does not work

| Symptom | Check |
|---|---|
| Nothing happens, no log line | Topic missing from the subscribe list in `on_connect()` (Step 6) |
| Log says "unknown topic" | Topic spelled differently in Python and Swift — they must match exactly, and MQTT is case sensitive |
| Log says "Invalid command" | The app is sending a word your `valid_commands` dictionary does not contain |
| Works with `mosquitto_pub`, not from the app | Swift side — check Steps 11–14 |
| Button flips back by itself | Missing revert line (Step 13), or the Pi returned an error |
| Button stays on but nothing moves | Wiring or pin number, not code. Test the pin with `gpio_test.py` |
| Another device stopped working | Pin clash — two devices on the same GPIO number |
| Buzzer silent but pin is HIGH | Passive buzzer needs PWM, not a plain HIGH |

**Always work in this order:** wire it, test the pin, test with `mosquitto_pub`,
then add the app. Each stage rules out one whole layer.

---

## See also

- `WIRING_GUIDE.md` — identifying components and breadboard layout
- `SERVO_TUNING_GUIDE.md` — adjusting angles, direction and speed
- `TEACHING_GUIDE.md` — how the message travels from the iPad to the Pi
- `gpio_test.py` — hardware test for the pins already in the project
