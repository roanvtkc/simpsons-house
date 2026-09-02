# Servo Tuning Guide — Simpson's House

How to change how far the front door and garage door open, which way they
swing, and how fast they move.

Every model is cut and glued slightly differently, so the angles in the repo
are a starting point, not the right answer. Expect to tune them.

---

## The short version

If you just want to change how far a door opens, these five steps are the whole job.

**1. Stop the service** (it holds the GPIO pins):
```bash
sudo systemctl stop simpsons-house.service
```

**2. Find your angles** by jogging the servo:
```bash
python3 servo_calibrate.py
```
Type `g` for garage or `d` for front door, then type angles (`0`, `45`, `90`) and watch the door. Write down the number where it looks shut and the number where it looks open.

**3. Open `mqttlistener.py`** and find the line for your door:

| Door | Function | Find this line |
|---|---|---|
| Garage | `control_garage_door()` | `angle = 90 if open_door else 0` |
| Front door | `control_door()` | `angle = 90 if state else 0` |

**4. Put your two numbers in.** The first number is OPEN, the second is CLOSED. If your garage looked right at 60 open and 5 shut:

```python
# before
angle = 90 if open_door else 0
# after
angle = 60 if open_door else 5
```

**5. Start the service again** and test from the iPad:
```bash
sudo systemctl start simpsons-house.service
```

That is it. The rest of this guide explains why those numbers work, how to reverse a door that opens the wrong way, and how to slow the movement down.

---

## Before you start

**Stop the service first.** The background service holds the GPIO pins. If you
run a test script while it is running, both programs fight over the same servo
and you get twitching and confusing results:

```bash
sudo systemctl stop simpsons-house.service
```

Start it again when you have finished tuning:

```bash
sudo systemctl start simpsons-house.service
```

**Golden rules:**
- Change one number at a time, then test
- If a servo buzzes or gets warm, stop — it is straining, not working
- Never force a door by hand while the servo is powered

---

## How a servo hears an angle

A servo does not understand degrees. It listens for a pulse, repeated 50 times
a second, and moves to the position that pulse length represents.

```
   one cycle = 20 ms  (50 Hz)
   |<--------------------------------->|
    ____                                ____
   |    |______________________________|    |____
   |<-->|
   pulse length decides the position

   0.4 ms  ->    0 degrees
   1.4 ms  ->   90 degrees
   2.4 ms  ->  180 degrees
```

`mqttlistener.py` converts your angle into that pulse inside
`set_servo_angle()`:

```python
duty = (angle / 180.0) * 10 + 2
```

Duty cycle is the percentage of each cycle the pulse is switched on. So
**0 degrees = 2%**, **90 degrees = 7%**, **180 degrees = 12%**.

Two lines below it are easy to misread:

```python
time.sleep(0.8)          # wait for the servo to physically arrive
pwm.ChangeDutyCycle(0)   # stop pulsing so it does not hum
```

The `sleep` is a **wait**, not a speed setting. The servo always travels at
full speed. Making the sleep longer just adds a pause after it arrives.
See [Changing the speed](#changing-the-speed) for how to actually slow it down.

Cutting the signal afterwards means the servo stops holding its position. It
runs cooler and quieter, but the door can be nudged open by hand. That is
deliberate.

---

## The two lines you will edit

Both doors use the same helper. Only the angles differ.

| Door | Function in `mqttlistener.py` | The line |
|---|---|---|
| Garage | `control_garage_door()` | `angle = 90 if open_door else 0` |
| Front door | `control_door()` | `angle = 90 if state else 0` |

Read it as: **open = 90 degrees, closed = 0 degrees.**

Pins, for reference (BCM numbering, set near the top of the file):

| Door | GPIO | Physical pin |
|---|---|---|
| Garage servo | 27 | 13 |
| Front door servo | 23 | 16 |

---

## Finding your angles

Rather than guessing and restarting the service each time, jog the servo live.

```bash
sudo systemctl stop simpsons-house.service
python3 servo_calibrate.py
```

At the prompt:

| Type this | What happens |
|---|---|
| `g` | switch to the garage servo |
| `d` | switch to the front door servo |
| `90` | move to 90 degrees |
| `s 0 90 2.5` | sweep 0 to 90 degrees over 2.5 seconds |
| `hold` | keep the servo powered so it resists being moved |
| `release` | stop pulsing after each move (the default) |
| `q` | quit and clean up the pins |

It prints the duty cycle and pulse width next to every move, which makes the
maths above concrete for students.

**Method:**
1. Type `0` and look at the door. Is it properly shut?
2. Work upwards — `20`, `40`, `60` — until it looks properly open.
3. Note those two numbers. They are your closed and open angles.
4. Put them into the two lines above.
5. Restart the service and test from the iPad.

---

## Setting the travel

If the garage door looks fully open at 60 degrees, edit `control_garage_door()`:

```python
angle = 60 if open_door else 0
```

Closed does not have to be 0 either. If the door is slightly ajar at 0, try:

```python
angle = 60 if open_door else 8
```

---

## Reversing the direction

If a servo opens the door the wrong way, swap the two numbers instead of
remounting the servo:

```python
angle = 0 if open_door else 90
```

---

## Changing the speed

A default move snaps the door open — an SG90 covers about 60 degrees in a tenth
of a second. To make it swing, step through the positions in between.

Add this function to `mqttlistener.py`, next to `set_servo_angle()`:

```python
def sweep_servo_angle(pwm, start, end, label="Servo", seconds=1.5, steps=50):
    """Move gradually from start to end so the door swings instead of snapping."""
    try:
        for i in range(steps + 1):
            angle = start + (end - start) * (i / steps)
            pwm.ChangeDutyCycle((angle / 180.0) * 10 + 2)
            time.sleep(seconds / steps)
        pwm.ChangeDutyCycle(0)
        logger.info(f"{label} swept {start} -> {end} degrees over {seconds}s")
        return True
    except Exception as e:
        logger.error(f"Servo sweep failed ({label}): {e}")
        return False
```

Then call it from `control_garage_door()`:

```python
start, end = (0, 90) if open_door else (90, 0)
success = sweep_servo_angle(GARAGE_SERVO_PWM, start, end,
                            label="Garage Door Servo", seconds=2.0)
```

- Larger `seconds` — slower
- More `steps` — smoother; below about 20 the movement looks steppy

Try `s 0 90 2.5` in the calibration script first to pick a speed you like.

> **Watch the power.** A slow sweep draws current for longer. If the Pi resets
> when both doors move together, stagger them or move to an external 5V supply.

---

## Do not forget the log messages

Just below each angle line, the log text has the old value written into it:

```python
logger.info(f"Garage Door -> {'OPEN (90°)' if open_door else 'CLOSED (0°)'}")
```

If you change the angle to 60, update this too, or your logs will lie to you
during troubleshooting.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Buzzing, servo warm | Angle is past the mechanical stop | Back off 10–15 degrees. Most SG90s only reach about 170, not 180 |
| Constant small twitching | Software PWM jitter | Normal. The code already drops to `ChangeDutyCycle(0)` after each move |
| Pi reboots when a door moves | Both servos browning out the 5V rail | Stagger the doors, or use an external 5V supply with common ground |
| Door moves the wrong way | Servo mounted mirrored | Swap the two angle numbers |
| Door creeps open by itself | Signal released, servo not holding | Expected. Use `hold` behaviour only if you really need it |
| Nothing moves at all | Service still running and holding the pins | `sudo systemctl stop simpsons-house.service` first |
| Moves in the test script, not from the iPad | Service not restarted after editing | `sudo systemctl restart simpsons-house.service` |

---

## Quick reference

```
Stop service      sudo systemctl stop simpsons-house.service
Calibrate         python3 servo_calibrate.py
Edit angles       mqttlistener.py -> control_garage_door() / control_door()
Restart service   sudo systemctl restart simpsons-house.service
Watch the logs    journalctl -u simpsons-house.service -f
```

| Angle | Duty | Pulse |
|---|---|---|
| 0° | 2% | 0.4 ms |
| 45° | 4.5% | 0.9 ms |
| 90° | 7% | 1.4 ms |
| 135° | 9.5% | 1.9 ms |
| 180° | 12% | 2.4 ms |
