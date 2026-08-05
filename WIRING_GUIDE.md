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

## Device 2 — Garage Door (Servo Motor)

The garage door uses the same kind of SG90 hobby servo as the front door, just on
a different GPIO pin. No driver board is needed — three wires straight to the Pi.

```
  ┌─────────────────┐  3 wires  ┌──────────────────┐
  │  Raspberry Pi   │──────────>│   SG90 Servo     │
  │  GPIO 27        │  signal   │   (garage door)  │
  │  5V, GND        │  power    │                  │
  └─────────────────┘           └──────────────────┘
```

A servo has a motor, gearbox and position sensor built in. You tell it *where* to
go as an angle, and it holds that position by itself — unlike a stepper, which has
to be driven coil by coil.

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

### Wire connections (step by step)

| Step | Servo wire | Colour | From | To |
|------|-----------|--------|------|----|
| 1 | Signal | Orange or Yellow or White | Servo signal wire | Pi GPIO 27 (physical pin 13) |
| 2 | Power | Red | Servo red wire | Pi 5V (physical pin 2) |
| 3 | Ground | Brown or Black | Servo brown/black wire | Pi GND (physical pin 14) |

> **Why 5V and not 3.3V?** The SG90 needs 5V to develop full torque. The signal
> wire is happy with the Pi's 3.3V logic — only the power wire must be 5V.

> **Note the pins are different from the front door.** Garage door is GPIO 27
> (pin 13); front door is GPIO 23 (pin 16). Swapping them makes the wrong door move.

### How the Pi controls the angle

```
Pi GPIO 27 ──> 50 Hz pulse train, pulse width 1ms–2ms
                        ↓
        servo's internal circuit compares pulse width to
        its position sensor and drives the motor until they match
                        ↓
              horn holds at the requested angle
```

In code this is a PWM duty cycle: 0° → 2%, 180° → 12%. The firmware uses
**0° = closed, 90° = open**, then sets the duty cycle to 0 so the servo stops
pulsing and doesn't hum while idle.

### Test it

```bash
python3 gpio_test.py
```

**Watch for:** the servo horn swings roughly a quarter turn, pauses, then swings
back. If it buzzes without moving, check the red wire is on 5V.

### Servo troubleshooting

| Symptom | Most likely cause | Fix |
|---------|-------------------|-----|
| Servo doesn't move at all | Signal wire on the wrong pin | Garage is GPIO 27 (pin 13), not GPIO 23 |
| Servo buzzes but barely moves | Powered from 3.3V instead of 5V | Move the red wire to a 5V pin |
| Servo doesn't move at all | Common GND missing | Check the brown/black wire to Pi GND |
| Servo hums continuously when idle | Still being sent pulses | The code should call `ChangeDutyCycle(0)` after each move |
| Servo moves the wrong way | Angles mapped the other way round | Swap the values in `control_garage_door()` |
| Servo won't reach full travel | SG90 unit variation, or door binding | Adjust the 2%–12% range in `set_servo_angle()`; check the door moves freely |
| Pi reboots when the servo moves | Both servos drawing peak current at once | Add an external 5V supply, GND common with the Pi |

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

**Garage Door Servo:**
- [ ] Signal wire (orange/yellow/white): Servo → Pi GPIO 27 (pin 13)
- [ ] Power wire (red): Servo → Pi 5V (pin 2)
- [ ] Ground wire (brown/black): Servo → Pi GND (pin 14)

**Front Door Servo:**
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

🚗 TEST 2/3 — Garage Door Servo (GPIO 27)
   → Watch the servo arm: it should move to 90° then return to 0°
✅ Garage door servo test PASSED

🚪 TEST 3/3 — Front Door Servo (GPIO 23)
   → Watch the servo arm: it should move to 90° then return to 0°
✅ Front door servo test PASSED

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
  Pin  2     5V      Garage servo power  + (not a GPIO, just power)
  Pin  4     5V      Front door servo power + (not a GPIO, just power)
  Pin  6     GND     Front door servo GND  − (not a GPIO, just ground)
  Pin  9     GND     LED GND      − (not a GPIO, just ground)
  Pin 11     GPIO 17 LED (light)
  Pin 13     GPIO 27 Garage door servo signal
  Pin 14     GND     Garage servo GND    − (not a GPIO, just ground)
  Pin 16     GPIO 23 Front door servo signal
```

Run `pinout` on the Pi to see a colour-coded version of this on your screen.
