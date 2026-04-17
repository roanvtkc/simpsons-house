# Wiring Guide — Simpson's House

Work through each section in order. Wire one device, test it, then move on.
Never wire everything at once — it makes faults much harder to find.

---

## Before you start

**Run this command on the Pi first:**
```bash
pinout
```
It prints a colour-coded diagram of the physical board. Keep it open in a second terminal window while you wire. Every pin number in this guide refers to the **GPIO (BCM) number**, not the physical pin position.

**Golden rules:**
- Always power the Pi OFF before adding or removing wires
- One wire at a time — plug in, check, then plug in the next
- If something smells hot, power off immediately

---

## Device 1 — Living Room Light (LED)

### Identifying the LED

An LED has two legs. They are NOT the same:

```
     ___
    /   \
   | LED |
    \___/
      |  \
      |   \
   LONG   SHORT
   leg    leg
    (+)   (-)
  Anode  Cathode
```

- **Longer leg = Anode = positive (+)** — this connects toward the GPIO pin
- **Shorter leg = Cathode = negative (−)** — this connects toward GND
- The plastic body also has a **flat edge** on one side — the flat edge is always the cathode (−) side

> If you put the LED in backwards it simply will not light. It will not break,
> just swap the legs around.

### Identifying the resistor

A 220Ω resistor has colour bands: **Red – Red – Brown – Gold**.

```
   __|__
  |     |     Red  = 2
  | 220 |     Red  = 2
  |_____|     Brown = × 10
    | |       Gold  = ± 5%
              → 22 × 10 = 220Ω
```

Resistors have no polarity — either leg can go in either direction.

### Where to place it on the breadboard

The breadboard has two halves (top rows a–e, bottom rows f–j) connected across the middle gap. Columns are numbered. Power rails run along the long edges.

```
   Breadboard (top view)
   ┌────────────────────────────────────────┐
   │  + rail ································│  ← 5V (not used here)
   │  - rail ································│  ← GND rail
   │                                        │
   │  a b c d e   f g h i j                 │
   │  ─────────   ─────────                 │
   │  [col 1  ]   [      ]     row 1        │
   │  [col 2  ]   [      ]     row 2        │
   │  [col 3  ]   [      ]     row 3        │
   │  [col 4  ]   [      ]     row 4        │
   │  [col 5  ]   [      ]     row 5        │
   │                                        │
   │  + rail ································│  ← 5V (not used here)
   │  - rail ································│  ← GND rail
   └────────────────────────────────────────┘
```

**Place the LED across the centre gap:**
- Long leg (+) → column e, row 3 (left half)
- Short leg (−) → column f, row 3 (right half)

**Place the resistor in the left half:**
- One leg → column a, row 1
- Other leg → column a, row 3 (same row as the LED's long leg)

### Wire connections (step by step)

Make these connections ONE AT A TIME:

| Step | From | To | Wire colour suggestion |
|------|------|----|------------------------|
| 1 | Pi GPIO 17 (physical pin 11) | Breadboard column a, row 1 | Yellow |
| 2 | Breadboard column a, row 1 | Resistor leg 1 | — (resistor bridges rows 1–3) |
| 3 | Resistor leg 2 | Column a, row 3 → LED anode (+, long leg) in column e, row 3 | — (resistor & LED in same half) |
| 4 | LED cathode (−, short leg) column f, row 3 | GND rail | Black |
| 5 | GND rail | Pi GND (physical pin 9) | Black |

### Circuit in plain English

```
Pi GPIO 17 → 220Ω resistor → LED (+) long leg → through LED → LED (−) short leg → GND → Pi GND
```

### Test it

```bash
python3 gpio_test.py
```

**Watch for:** the LED blinks 3 times (0.5 s on, 0.5 s off). If nothing happens, see Troubleshooting below.

### LED troubleshooting

| Symptom | Most likely cause | Fix |
|---------|-------------------|-----|
| LED doesn't light | LED in backwards | Swap the two legs |
| LED doesn't light | Wrong GPIO pin | Re-check pin 11 on `pinout` |
| LED doesn't light | Resistor not bridging rows | Check rows — resistor must connect column a row 1 to column a row 3 |
| LED is very dim | Resistor too high (wrong value) | Check colour bands: Red–Red–Brown–Gold |
| LED lights permanently, won't turn off | Short circuit somewhere | Power off, check no wires touching |

---

## Device 2 — Garage Door (Stepper Motor + ULN2003 Driver Board)

### Understanding the two-board system

You have TWO boards for this device:

```
  ┌─────────────────┐         ┌──────────────────────┐
  │  Raspberry Pi   │ 4 wires │   ULN2003 Driver     │
  │  GPIO 27,18,    │────────>│   Board              │  5V power
  │       22,24     │         │   (the blue board)   │<──────────
  └─────────────────┘         └──────┬───────────────┘
                                     │ 5-pin connector
                               ┌─────┴──────────────┐
                               │  28BYJ-48 Stepper   │
                               │  Motor              │
                               │  (the small motor   │
                               │   with a white plug) │
                               └─────────────────────┘
```

The Pi can only supply ~16mA per pin — not enough to spin a motor. The ULN2003 board contains transistors that take the Pi's weak signal and use 5V power to drive the motor coils.

### Identifying the ULN2003 board

The ULN2003 board has labelled connectors. Look for:

```
  ┌─────────────────────────────────────┐
  │  ULN2003 DRIVER BOARD               │
  │                                     │
  │  ○ IN1    ← wire from GPIO 27       │
  │  ○ IN2    ← wire from GPIO 18       │
  │  ○ IN3    ← wire from GPIO 22       │
  │  ○ IN4    ← wire from GPIO 24       │
  │  ○ IN5    ← NOT USED (leave empty)  │
  │                                     │
  │  ┌──────┐  ← 5-pin motor connector  │
  │  │ motor│     (motor plugs in here) │
  │  └──────┘                           │
  │                                     │
  │  ○ VCC (or +)  ← 5V power           │
  │  ○ GND (or −)  ← Ground             │
  │                                     │
  └─────────────────────────────────────┘
```

The labels `IN1` through `IN4` are usually printed in white text on the blue board. The 5-pin motor connector is on the opposite end.

### Identifying the stepper motor connector

The 28BYJ-48 motor has a white 5-pin plug on a short cable:

```
  Motor cable:   ┌─────────────────────┐
                 │  ○  ○  ○  ○  ○      │  ← 5-pin keyed plug
                 └─────────────────────┘
                   ↑
                   Notch/tab on one side — it only fits ONE way into the ULN2003 board
```

Just push the plug firmly into the 5-pin socket on the ULN2003 board. It is keyed — it physically cannot go in upside down.

### Wire connections (step by step)

**First: plug the motor into the board**
- Push the 28BYJ-48 white plug into the 5-pin connector on the ULN2003 board
- You should hear/feel a small click when it seats properly

**Then connect the Pi to the ULN2003 board:**

| Step | From | To | Wire colour suggestion |
|------|------|----|------------------------|
| 1 | Pi GPIO 27 (physical pin 13) | ULN2003 IN1 | Blue |
| 2 | Pi GPIO 18 (physical pin 12) | ULN2003 IN2 | Green |
| 3 | Pi GPIO 22 (physical pin 15) | ULN2003 IN3 | Yellow |
| 4 | Pi GPIO 24 (physical pin 18) | ULN2003 IN4 | Orange |
| 5 | Pi 5V (physical pin 2) | ULN2003 VCC (or +) | Red |
| 6 | Pi GND (physical pin 14) | ULN2003 GND (or −) | Black |

> **Why do we use Pi 5V (not 3.3V) for the ULN2003?**
> The stepper motor coils need 5V to reach full torque. The IN1–IN4 control
> signals from the Pi are 3.3V but the ULN2003 accepts them — only the motor
> power line needs to be 5V.

### The order of IN1–IN4 matters

If the wires are in the wrong order, the stepper sequence breaks and the motor will vibrate or stall rather than rotate. Double-check each wire against the table above.

### Circuit in plain English

```
Pi GPIO 27 → ULN2003 IN1 ─┐
Pi GPIO 18 → ULN2003 IN2  │
Pi GPIO 22 → ULN2003 IN3  ├─ transistors amplify signals using 5V power
Pi GPIO 24 → ULN2003 IN4 ─┘
Pi 5V      → ULN2003 VCC
Pi GND     → ULN2003 GND → also provides return path for motor current
                        ↓
               28BYJ-48 motor coils energised in sequence → shaft rotates
```

### Test it

```bash
python3 gpio_test.py
```

**Watch for:** the motor shaft (or the white plastic gear visible through the hole) turns one direction for ~2 seconds, pauses, then turns the other direction for ~2 seconds.

### Stepper motor troubleshooting

| Symptom | Most likely cause | Fix |
|---------|-------------------|-----|
| Motor hums/vibrates but doesn't spin | IN1–IN4 wired in wrong order | Re-check each wire against the table |
| Motor doesn't move at all | 5V not connected to ULN2003 VCC | Check the red 5V wire |
| Motor doesn't move at all | Common GND missing | Check the black GND wire |
| Motor gets hot and stops | Steps too fast, motor stalling | Increase the delay in `stepper_step()` |
| Motor spins but in wrong direction | Sequence reversed in firmware | Swap "forward" and "reverse" in `rotate_stepper()` |
| Motor plug feels loose | Not fully seated | Push the white plug firmly until it clicks |

---

## Device 3 — Front Door (Servo Motor)

### Identifying the servo wires

Most SG90 hobby servos have three wires. The colours can vary between brands:

```
  Common wire colours for SG90 servos:
  ┌──────────┬──────────┬──────────┐
  │  Signal  │  Power   │  Ground  │
  │  (data)  │  (VCC)   │  (GND)   │
  ├──────────┼──────────┼──────────┤
  │  Orange  │  Red     │  Brown   │  ← most common
  │  Yellow  │  Red     │  Black   │  ← some brands
  │  White   │  Red     │  Black   │  ← some brands
  └──────────┴──────────┴──────────┘

  When in doubt: RED is always power (VCC, 5V)
```

The three wires come out of the servo in a small 3-pin connector. The connector can be pushed directly onto male header pins or used with jumper wires.

### The servo connector orientation

```
  Servo 3-pin plug (looking at the pins head-on):
  ┌─────────────────────┐
  │   ○     ○     ○     │
  └─────────────────────┘
   Signal  VCC   GND
  (Orange) (Red) (Brown)

  Note: order may vary — always check the wire colours, not just position
```

### Wire connections (step by step)

| Step | Servo wire | Colour | From | To |
|------|-----------|--------|------|----|
| 1 | Signal | Orange or Yellow or White | Servo signal wire | Pi GPIO 23 (physical pin 16) |
| 2 | Power | Red | Servo red wire | Pi 5V (physical pin 4) |
| 3 | Ground | Brown or Black | Servo brown/black wire | Pi GND (physical pin 6) |

> **Only three wires for the servo.** It does not need a driver board — the SG90
> draws little enough current that the Pi's 5V pin can power it directly.

### Circuit in plain English

```
Pi GPIO 23 → Servo SIGNAL wire  (orange/yellow/white)
Pi 5V      → Servo POWER wire   (red)
Pi GND     → Servo GROUND wire  (brown/black)

The servo contains its own motor + gearbox + position sensor.
Sending a PWM signal on the signal wire tells the servo what angle to go to.
```

### What 0° and 90° look like

When you run the test, the servo arm moves:
- **0°** — arm rotated fully to one end stop (the "closed door" position)
- **90°** — arm rotated 90° from that point (the "open door" position)

Exactly which physical direction that is depends on how you mount the servo. If it opens the wrong way, change the angles in `control_door()`:
```python
angle = 90 if state else 0   # change 90 to 180 if the arm moves the wrong way
```

### Test it

```bash
python3 gpio_test.py
```

**Watch for:** the servo arm sweeps from one position to 90°, holds for half a second, then returns to 0°.

### Servo troubleshooting

| Symptom | Most likely cause | Fix |
|---------|-------------------|-----|
| Servo doesn't move | Signal wire on wrong pin | Check orange/yellow wire → GPIO 23 (pin 16) |
| Servo twitches but doesn't hold position | Power wire not connected | Check red wire → 5V (pin 4) |
| Servo buzzes constantly | PWM not stopping after move | Check `SERVO_PWM.ChangeDutyCycle(0)` is called in `set_servo_angle()` |
| Servo moves to wrong position | Wrong duty cycle | Try changing the `angle` value in `control_door()` |
| Servo arm moves backwards | Mounted upside down | Physically flip the servo, or swap 0 and 90 in the code |

---

## Full wiring check — do this before first boot

Go through this checklist out loud with a partner. One person reads, one person points to each wire:

**LED:**
- [ ] Yellow wire: Pi GPIO 17 (pin 11) → resistor leg 1
- [ ] Resistor bridges to LED long leg (+) in same breadboard half
- [ ] LED short leg (−) → GND rail
- [ ] Black wire: GND rail → Pi GND (pin 9)

**Stepper Motor:**
- [ ] Motor white plug seated in ULN2003 5-pin connector (clicked in)
- [ ] Blue wire: Pi GPIO 27 (pin 13) → ULN2003 IN1
- [ ] Green wire: Pi GPIO 18 (pin 12) → ULN2003 IN2
- [ ] Yellow wire: Pi GPIO 22 (pin 15) → ULN2003 IN3
- [ ] Orange wire: Pi GPIO 24 (pin 18) → ULN2003 IN4
- [ ] Red wire: Pi 5V (pin 2) → ULN2003 VCC
- [ ] Black wire: Pi GND (pin 14) → ULN2003 GND

**Servo:**
- [ ] Signal wire (orange/yellow/white): Servo → Pi GPIO 23 (pin 16)
- [ ] Power wire (red): Servo → Pi 5V (pin 4)
- [ ] Ground wire (brown/black): Servo → Pi GND (pin 6)

**Run the test:**
```bash
python3 gpio_test.py
```

Expected output:
```
🏠 Simpson's House GPIO Test
──────────────────────────────
💡 TEST 1/3 — Living Room Light
   → Watch the LED: it should blink ON–OFF 3 times
✅ Light test passed

🌀 TEST 2/3 — Garage Door Stepper Motor
   → Watch the motor shaft: it should turn one way, then reverse
✅ Stepper test passed

🚪 TEST 3/3 — Front Door Servo
   → Watch the servo arm: it should move to 90° then return to 0°
✅ Servo test passed

🏁 All tests passed — ready to run the full Simpson's House system!
```

If any test fails, see the troubleshooting table for that device above.

---

## Quick reference — GPIO pin map

The physical board has 40 pins. These are the ones we use:

```
  Physical   GPIO    Used for
  Pin        (BCM)
  ─────────────────────────────
  Pin  2     5V      ULN2003 VCC + (not a GPIO, just power)
  Pin  4     5V      Servo power  + (not a GPIO, just power)
  Pin  6     GND     Servo GND    − (not a GPIO, just ground)
  Pin  9     GND     LED GND      − (not a GPIO, just ground)
  Pin 11     GPIO 17 LED (light)
  Pin 12     GPIO 18 Stepper IN2
  Pin 13     GPIO 27 Stepper IN1
  Pin 14     GND     ULN2003 GND  − (not a GPIO, just ground)
  Pin 15     GPIO 22 Stepper IN3
  Pin 16     GPIO 23 Servo signal
  Pin 18     GPIO 24 Stepper IN4
```

Run `pinout` on the Pi to see a colour-coded version of this on your screen.
