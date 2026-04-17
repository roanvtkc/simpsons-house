#!/usr/bin/env python3
"""
Simpson's House MQTT Listener and GPIO Controller
==================================================
This Python script runs on the Raspberry Pi and does two things:
  1. Listens for commands sent from the iPad app over the network (via MQTT)
  2. Controls the real hardware (LED, stepper motor, servo) using the Pi's GPIO pins

TEACHING: Think of this script as the "butler" of the smart house.
The iPad app shouts orders ("turn the light on!") and this script
physically carries them out by sending electrical signals to the hardware.

HOW IT ALL CONNECTS:
  iPad App  →  WiFi/WebSocket  →  Mosquitto (MQTT broker on Pi)  →  this script  →  GPIO pins  →  Hardware
"""

import paho.mqtt.client as mqtt  # Library that speaks the MQTT protocol
import RPi.GPIO as GPIO           # Library that controls the Pi's physical pins
import time                       # Used to add pauses (e.g. between stepper motor steps)
import logging                    # Used to print status messages to the terminal
import json                       # Used to format status updates as JSON (structured text)
import signal                     # Used to catch Ctrl+C and shutdown cleanly
import sys                        # Used to exit the program
from datetime import datetime     # Used to add timestamps to log messages

# =============================================================================
# SECTION 1: CONFIGURATION
# =============================================================================
# TEACHING: These are all the settings in one place. Changing a number here
# changes how the whole program behaves. This is good practice — never
# scatter magic numbers throughout your code.

# GPIO pin assignments — these match the physical wires you plugged in.
# BCM numbering means we use the chip's numbers (GPIO 17), NOT the
# board's physical pin positions (which would be pin 11 for GPIO 17).
LIGHT_PIN = 17              # Living Room Light (LED + 220Ω resistor on GPIO 17)
STEPPER_PINS = [27, 18, 22, 24]  # Garage door: 4 pins drive the ULN2003 stepper motor
SERVO_PIN = 23              # Front Door Servo signal wire

# How many stepper motor steps = one full open or close action.
# Increase this number to make the garage door travel further.
GARAGE_TRAVEL_STEPS = 100

# MQTT broker address — "localhost" means "on this same Raspberry Pi".
# The broker is a separate program (Mosquitto) that routes messages.
BROKER_HOST = "localhost"
BROKER_PORT = 1883   # Standard MQTT port (TCP)
KEEPALIVE   = 60     # Send a heartbeat ping every 60 seconds so the connection stays alive

# TEACHING: MQTT uses "topics" like channels on a walkie-talkie.
# The iPad publishes a message to a topic, and this script subscribes to the same
# topic to receive it. Both sides must use the EXACT same topic string.
TOPIC_LIGHT  = "home/light"    # iPad sends "ON" or "OFF" here
TOPIC_GARAGE = "home/garage"   # iPad sends "OPEN" or "CLOSE" here
TOPIC_DOOR   = "home/door"     # iPad sends "ON" or "OFF" here

# Topics this script publishes status back to the iPad on:
TOPIC_STATUS = "home/status"   # Full JSON snapshot of all device states
TOPIC_SYSTEM = "home/system"   # System info (version, GPIO pins used, etc.)

# TEACHING: Python dictionaries are great for tracking state.
# This keeps track of whether each device is currently ON or OFF.
# True = on/open, False = off/closed
device_states = {
    "light":  False,
    "garage": False,
    "door":   False
}

# Extra tracking just for the garage motor so we know if it's moving
# and how far it has travelled.
motor_state = {
    "running":     False,
    "position":    0,       # cumulative steps moved from the starting position
    "last_action": "close"
}

# These are set up later in main() — we use "global" to share them
# between functions without passing them as parameters every time.
client    = None  # The MQTT client object
SERVO_PWM = None  # The PWM (pulse-width modulation) controller for the servo

# =============================================================================
# SECTION 2: LOGGING
# =============================================================================
# TEACHING: Instead of using print(), professional code uses a logging
# library. It automatically adds timestamps and severity levels (INFO,
# WARNING, ERROR) so you can filter messages and understand what went wrong.

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] Simpson's House: %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# =============================================================================
# SECTION 3: GPIO SETUP
# =============================================================================
# TEACHING: Before you can use a GPIO pin you must:
#   1. Tell the Pi which numbering scheme you're using (BCM vs BOARD)
#   2. Tell each pin whether it is an INPUT (reading a sensor) or
#      OUTPUT (driving a component)
#   3. Set its initial state (HIGH = 3.3V, LOW = 0V / GND)

def setup_gpio():
    """
    Configure all GPIO pins used by Simpson's House.

    TEACHING: This function runs once at startup. Think of it like
    plugging appliances into sockets — you do it once, then use them.
    """
    logger.info("🏠 Initializing Simpson's House GPIO...")

    GPIO.setmode(GPIO.BCM)      # Use BCM chip numbers (matches our LIGHT_PIN = 17 etc.)
    GPIO.setwarnings(False)     # Suppress "pin already in use" warnings on restart

    # Set up the light pin as an output, starting LOW (off)
    GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)

    # The stepper motor needs 4 output pins — loop sets them all up
    for pin in STEPPER_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    # Set up the servo signal pin as an output, starting LOW
    GPIO.setup(SERVO_PIN, GPIO.OUT, initial=GPIO.LOW)

    # TEACHING: PWM = Pulse Width Modulation. Instead of just HIGH or LOW,
    # PWM rapidly switches the pin on/off at a set frequency. The ratio of
    # on-time to off-time (duty cycle) controls the servo's angle.
    # 50 Hz is the standard frequency for hobby servo motors.
    global SERVO_PWM
    SERVO_PWM = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz PWM on the servo pin
    SERVO_PWM.start(0)                    # Start with 0% duty cycle (servo off)

    logger.info(f"💡 Light pin: GPIO {LIGHT_PIN}")
    logger.info(f"🚗 Garage stepper pins: {STEPPER_PINS}")
    logger.info(f"🚪 Door servo pin: GPIO {SERVO_PIN}")


def set_servo_angle(angle: int) -> bool:
    """
    Move the servo motor to an angle between 0 and 180 degrees.

    TEACHING: A servo motor has a built-in gearbox and position sensor.
    You tell it WHERE to go (as an angle), not how to get there.
    The duty cycle formula maps 0° → 2% and 180° → 12%.

    Why 2% and 12%? That's the standard pulse width range (1ms–2ms)
    at 50 Hz that SG90-type hobby servos understand.
    """
    try:
        if not 0 <= angle <= 180:
            logger.error(f"Invalid servo angle: {angle}. Must be 0-180.")
            return False

        # Convert the 0-180° range into the 2-12% duty cycle range
        duty = (angle / 180.0) * 10 + 2
        SERVO_PWM.ChangeDutyCycle(duty)
        time.sleep(0.8)            # Wait 0.8 seconds for the servo to physically move
        SERVO_PWM.ChangeDutyCycle(0)  # Stop sending pulses to prevent jitter/humming

        logger.info(f"🚪 Door servo → {angle}°")
        return True

    except Exception as e:
        logger.error(f"❌ Servo control failed: {e}")
        return False


# =============================================================================
# SECTION 4: STEPPER MOTOR CONTROL
# =============================================================================
# TEACHING: A stepper motor moves in tiny fixed "steps" (not continuous spin).
# We control it with 4 wires. By energising these wires in a specific
# repeating pattern (the STEP_SEQUENCE), the motor turns one step at a time.
#
# "Half-stepping" (8 patterns instead of 4) gives smoother movement
# and finer position control at the cost of slightly less torque.
#
# The ULN2003 driver board sits between the Pi and the motor because
# the Pi's GPIO pins can only supply ~16mA — not enough to drive a motor.
# The ULN2003 uses transistors to amplify that signal using 5V power.

STEP_SEQUENCE = [
    #  IN1  IN2  IN3  IN4   ← ULN2003 input pins (driven by GPIO 27,18,22,24)
    [  1,   0,   0,   1  ],  # Step 1
    [  1,   0,   0,   0  ],  # Step 2
    [  1,   1,   0,   0  ],  # Step 3
    [  0,   1,   0,   0  ],  # Step 4
    [  0,   1,   1,   0  ],  # Step 5
    [  0,   0,   1,   0  ],  # Step 6
    [  0,   0,   1,   1  ],  # Step 7
    [  0,   0,   0,   1  ],  # Step 8 → then loop back to Step 1
]


def stepper_step(sequence, steps, delay=0.002):
    """
    Energise the stepper motor coils one step at a time.

    TEACHING: 'steps' is how many times we go through the full 8-pattern cycle.
    'delay' is how long we wait between each pattern — lower = faster motor,
    but too fast and the motor will stall (miss steps) or vibrate in place.
    """
    for _ in range(steps):             # Repeat for the number of requested steps
        for pattern in sequence:       # Go through each of the 8 coil patterns
            for pin, value in zip(STEPPER_PINS, pattern):  # Set each GPIO pin
                GPIO.output(pin, value)
            time.sleep(delay)          # Pause so the motor has time to physically move
    stop_stepper()                     # Always de-energise coils when done (saves power)


def rotate_stepper(direction: str, steps: int = 512):
    """
    Rotate the stepper motor forwards or backwards.

    TEACHING: Reversing the sequence list reverses the motor direction.
    That's how a stepper motor works — the order of coil energisation
    determines which way the shaft spins.
    """
    if direction == "forward":
        seq = STEP_SEQUENCE              # Normal order → opens the garage
    else:
        seq = list(reversed(STEP_SEQUENCE))  # Reversed order → closes the garage

    stepper_step(seq, steps)

    # Track position for diagnostics
    if direction == "forward":
        motor_state["position"] += steps
    else:
        motor_state["position"] = max(0, motor_state["position"] - steps)


def stop_stepper():
    """
    Cut power to all stepper motor coils.

    TEACHING: If you leave the coils energised after the motor stops,
    it draws current and heats up for no reason. Always de-energise
    when the motor is not actively moving.
    """
    for pin in STEPPER_PINS:
        GPIO.output(pin, GPIO.LOW)
    motor_state["running"] = False


# =============================================================================
# SECTION 5: MQTT EVENT HANDLERS
# =============================================================================
# TEACHING: MQTT uses an "event-driven" design. Instead of your code
# constantly checking "has a message arrived?", the library calls these
# callback functions FOR you whenever a specific event happens.
# This is sometimes called the "observer pattern".

def on_connect(client, userdata, flags, rc):
    """
    Called automatically by the MQTT library once the broker accepts our connection.

    TEACHING: 'rc' is the return code. 0 = success, anything else = failure.
    This is where we subscribe to topics — subscribing AFTER connecting
    ensures we don't miss any messages sent right at startup.
    """
    if rc == 0:
        logger.info("✅ Connected to Mosquitto MQTT broker")

        # Subscribe to the three device control topics
        # TEACHING: Subscribing means "I want to receive any message published to this topic".
        for topic in [TOPIC_LIGHT, TOPIC_GARAGE, TOPIC_DOOR]:
            client.subscribe(topic)
            logger.info(f"📡 Subscribed to: {topic}")

        # Announce that the controller is online
        publish_system_status("online", "Simpson's House controller started")

        # Send the current state of every device so the app can sync its display
        for device, state in device_states.items():
            publish_device_status(device, state)

    else:
        logger.error(f"❌ MQTT connection failed (code={rc}): {get_mqtt_error_message(rc)}")


def on_disconnect(client, userdata, rc):
    """Called automatically when the connection to the broker is lost."""
    if rc != 0:
        logger.warning(f"⚠️  Unexpected MQTT disconnection (code={rc})")
    else:
        logger.info("📡 MQTT disconnected cleanly")


def on_message(client, userdata, msg):
    """
    Called automatically whenever a message arrives on any subscribed topic.

    TEACHING: This is the heart of the backend. The flow is:
      1. Decode the raw bytes into a readable string
      2. Work out WHICH device the message is for (based on the topic)
      3. Check the command is valid (ON/OFF/OPEN/CLOSE)
      4. Call the matching hardware control function
      5. Publish the new status back to the app so the UI updates

    Think of this function as the call-centre operator — every command
    from the iPad comes through here first.
    """
    try:
        topic   = msg.topic
        payload = msg.payload.decode().strip().upper()  # e.g. b"on" → "ON"

        logger.info(f"📨 Command received: {topic} → {payload}")

        success       = False
        device_name   = ""
        command_state = None
        device_key    = topic.split('/')[-1]  # "home/light" → "light"

        # ── Route by topic ──────────────────────────────────────────────────
        # TEACHING: Each branch maps a topic to a device and validates the
        # command. We use a dictionary (valid_commands) to convert the string
        # command ("ON") into a boolean (True) that our functions understand.

        if topic == TOPIC_LIGHT:
            valid_commands = {"ON": True, "OFF": False}
            device_name    = "Living Room Light"
            command_state  = valid_commands.get(payload)  # None if unrecognised
            if command_state is None:
                publish_error(topic, f"Invalid command: {payload}. Use ON or OFF.")
                return
            success = control_light(command_state)

        elif topic == TOPIC_GARAGE:
            valid_commands = {"OPEN": True, "CLOSE": False}
            device_name    = "Garage Door"
            command_state  = valid_commands.get(payload)
            if command_state is None:
                publish_error(topic, f"Invalid command: {payload}. Use OPEN or CLOSE.")
                return
            success = control_garage_door(command_state)

        elif topic == TOPIC_DOOR:
            valid_commands = {"ON": True, "OFF": False}
            device_name    = "Front Door"
            command_state  = valid_commands.get(payload)
            if command_state is None:
                publish_error(topic, f"Invalid command: {payload}. Use ON or OFF.")
                return
            success = control_door(command_state)

        else:
            logger.warning(f"⚠️  Message on unknown topic: {topic}")
            return

        # ── Report result ───────────────────────────────────────────────────
        if success and command_state is not None:
            device_states[device_key] = command_state       # Update our state tracker
            publish_device_status(device_key, command_state) # Tell the app what changed
            logger.info(f"✅ {device_name} command executed successfully")
        else:
            logger.error(f"❌ {device_name} control failed")
            publish_error(topic, "Device control failed")

    except Exception as e:
        logger.error(f"❌ Message handling error: {e}")
        publish_error(msg.topic, f"Processing error: {str(e)}")


# =============================================================================
# SECTION 6: DEVICE CONTROL FUNCTIONS
# =============================================================================
# TEACHING: Each function here controls ONE physical device. They all follow
# the same pattern: try to do the action, log what happened, return True/False
# so the caller knows if it worked. This makes them easy to test in isolation.

def control_light(state: bool) -> bool:
    """
    Turn the living room LED on or off.

    TEACHING: GPIO.HIGH sends 3.3V to the pin. That voltage flows through
    the 220Ω resistor (which limits the current so the LED doesn't burn out)
    and then through the LED, causing it to emit light.
    GPIO.LOW sets the pin to 0V (GND), so no current flows and the LED goes off.
    """
    try:
        GPIO.output(LIGHT_PIN, GPIO.HIGH if state else GPIO.LOW)
        logger.info(f"💡 Living Room Light → {'ON' if state else 'OFF'}")
        return True
    except Exception as e:
        logger.error(f"❌ Light control error: {e}")
        return False


def control_garage_door(open_door: bool) -> bool:
    """
    Open or close the garage door by rotating the stepper motor.

    TEACHING: The motor only turns — it doesn't know where it is.
    We rely on rotating the same number of steps every time (GARAGE_TRAVEL_STEPS)
    to reliably open or close the door. If you change the physical setup
    you may need to adjust GARAGE_TRAVEL_STEPS at the top of this file.
    """
    try:
        motor_state["running"] = True

        if open_door:
            logger.info("🚗 Opening garage door — motor rotating forward...")
            rotate_stepper("forward", GARAGE_TRAVEL_STEPS)
        else:
            logger.info("🚗 Closing garage door — motor rotating in reverse...")
            rotate_stepper("reverse", GARAGE_TRAVEL_STEPS)

        motor_state["running"]     = False
        motor_state["last_action"] = "open" if open_door else "close"
        return True

    except Exception as e:
        logger.error(f"❌ Garage door error: {e}")
        motor_state["running"] = False
        return False


def control_door(state: bool) -> bool:
    """
    Open or close the front door servo.

    TEACHING: The servo understands angles, not on/off.
    We map the "open" concept to 90° and "closed" to 0°.
    You can change these angles to match how your servo is physically mounted.
    """
    try:
        angle   = 90 if state else 0  # OPEN = 90°, CLOSED = 0°
        success = set_servo_angle(angle)
        if success:
            logger.info(f"🚪 Front Door → {'OPEN (90°)' if state else 'CLOSED (0°)'}")
        return success
    except Exception as e:
        logger.error(f"❌ Door control error: {e}")
        return False


# =============================================================================
# SECTION 7: MOTOR UTILITY FUNCTIONS
# =============================================================================

def stop_garage_emergency():
    """
    Immediately cut power to the garage motor.

    TEACHING: An emergency stop ignores the normal flow — it just directly
    calls stop_stepper() to de-energise all motor coils right now.
    This is called on shutdown or crash so the motor isn't left on.
    """
    try:
        logger.warning("🚨 EMERGENCY GARAGE STOP")
        stop_stepper()
    except Exception as e:
        logger.error(f"❌ Emergency stop failed: {e}")


def get_garage_motor_status() -> dict:
    """Return a snapshot of the motor's current state (for diagnostics/debugging)."""
    return {
        "running":    motor_state["running"],
        "position":   motor_state["position"],
        "gpio_states": {
            f"pin{idx+1}": GPIO.input(pin)
            for idx, pin in enumerate(STEPPER_PINS)
        }
    }


# =============================================================================
# SECTION 8: MQTT PUBLISHING (sending data BACK to the iPad)
# =============================================================================
# TEACHING: MQTT is bi-directional. This section handles the Pi → iPad direction.
# After we carry out a command, we publish the new device state so the app's
# UI can update to reflect what actually happened on the hardware.

def publish_device_status(device: str, status: bool):
    """
    Publish the current state of a device back to the iPad app.

    TEACHING: 'retain=True' tells the Mosquitto broker to remember the last
    message on this topic. If the app reconnects later it will immediately
    receive the last known state without having to ask for it.
    """
    try:
        # Convert boolean to the string the app expects
        if device == "garage":
            status_msg = "OPEN" if status else "CLOSED"
        else:
            status_msg = "ON" if status else "OFF"

        client.publish(f"home/{device}/status", status_msg, retain=True)

        # For the garage, also publish detailed motor diagnostics
        if device == "garage":
            client.publish(
                f"home/{device}/motor_status",
                json.dumps(get_garage_motor_status()),
                retain=True
            )

        # Publish an overall snapshot of all device states
        system_status = {
            "timestamp":   datetime.now().isoformat(),
            "devices":     device_states.copy(),
            "garage_motor": motor_state.copy(),
            "controller":  "online"
        }
        client.publish(TOPIC_STATUS, json.dumps(system_status), retain=True)

    except Exception as e:
        logger.error(f"❌ Status publish error: {e}")


def publish_system_status(status: str, message: str = ""):
    """Publish the overall system information (version, pin layout, etc.)."""
    try:
        system_info = {
            "status":       status,
            "timestamp":    datetime.now().isoformat(),
            "message":      message,
            "version":      "3.2",
            "controller":   "Simpson's House GPIO Controller",
            "motor_driver": "ULN2003",
            "gpio_pins": {
                "light":           LIGHT_PIN,
                "garage_stepper":  STEPPER_PINS,
                "servo":           SERVO_PIN
            }
        }
        client.publish(TOPIC_SYSTEM, json.dumps(system_info), retain=True)
    except Exception as e:
        logger.error(f"❌ System status publish error: {e}")


def publish_error(topic: str, error_msg: str):
    """
    Publish an error description to a dedicated error topic.

    TEACHING: Publishing errors to a separate topic (e.g. home/light/error)
    means the app can subscribe to those topics and display the error in the
    UI without mixing error messages with normal status updates.
    """
    try:
        error_info = {
            "error":        error_msg,
            "timestamp":    datetime.now().isoformat(),
            "topic":        topic,
            "motor_status": get_garage_motor_status() if "garage" in topic else None
        }
        client.publish(f"{topic}/error", json.dumps(error_info))
    except Exception as e:
        logger.error(f"❌ Error publish failed: {e}")


# =============================================================================
# SECTION 9: UTILITY FUNCTIONS
# =============================================================================

def get_mqtt_error_message(rc: int) -> str:
    """Convert a numeric MQTT return code into a human-readable explanation."""
    return {
        1: "Incorrect protocol version",
        2: "Invalid client identifier",
        3: "Server unavailable",
        4: "Bad username or password",
        5: "Not authorized"
    }.get(rc, f"Unknown error (code {rc})")


# =============================================================================
# SECTION 10: SHUTDOWN HANDLING
# =============================================================================
# TEACHING: When the program receives a kill signal (e.g. you press Ctrl+C,
# or systemd stops the service), we want to:
#   • Stop the motor immediately so it doesn't stay energised
#   • Turn off all LEDs
#   • Tell the MQTT broker we are going offline
#   • Release the GPIO pins so other programs can use them
# Python's 'signal' module lets us hook into these OS-level events.

def signal_handler(signum, frame):
    """Called by the OS when the program receives SIGINT (Ctrl+C) or SIGTERM."""
    logger.info(f"🛑 Shutdown signal received ({signum}) — stopping gracefully...")
    cleanup_and_exit()


def cleanup_and_exit():
    """Safely shut down all hardware and network connections before exiting."""
    logger.info("🧹 Cleaning up Simpson's House...")

    try:
        stop_garage_emergency()    # Motor off first — safety priority
        GPIO.output(LIGHT_PIN, GPIO.LOW)  # Light off
        stop_stepper()             # All stepper coils off

        if SERVO_PWM:
            SERVO_PWM.stop()       # Stop generating PWM signal
        GPIO.cleanup()             # Release all GPIO pins back to the OS
        logger.info("✅ GPIO cleaned up")

    except Exception as e:
        logger.error(f"❌ GPIO cleanup error: {e}")

    try:
        if client and client.is_connected():
            publish_system_status("offline", "Controller shutting down")
            client.disconnect()
            logger.info("📡 MQTT disconnected")

    except Exception as e:
        logger.error(f"❌ MQTT cleanup error: {e}")

    logger.info("👋 Simpson's House stopped. Goodbye!")
    sys.exit(0)


# =============================================================================
# SECTION 11: ENTRY POINT (main)
# =============================================================================
# TEACHING: In Python, the block `if __name__ == "__main__":` means
# "only run main() when this file is executed directly" (not when it's
# imported by another script). main() is the function that starts everything.
#
# Startup sequence:
#   1. Register signal handlers (so Ctrl+C shuts down cleanly)
#   2. Initialise GPIO pins
#   3. Create and configure the MQTT client
#   4. Connect to the Mosquitto broker
#   5. Enter the event loop (loop_forever) — this blocks here and processes
#      incoming MQTT messages until the program is killed

def main():
    """Start the Simpson's House smart home controller."""
    global client

    logger.info("🏠 Starting Simpson's House Smart Home Controller v3.2")
    logger.info("📺 'D'oh! Welcome to the smartest house in Springfield!'")

    # Register OS signal handlers so we shut down cleanly on Ctrl+C or systemd stop
    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Step 1: Set up hardware
        setup_gpio()

        # Step 2: Create the MQTT client and attach our callback functions.
        # TEACHING: The MQTT library calls on_connect, on_disconnect, and
        # on_message automatically — we don't call them ourselves. We just
        # register them here and the library handles the timing.
        client = mqtt.Client(client_id="simpsons_house_controller")
        client.on_connect    = on_connect
        client.on_disconnect = on_disconnect
        client.on_message    = on_message

        # Step 3: Set a "last will" message.
        # TEACHING: If the Pi loses power unexpectedly (no clean disconnect),
        # the Mosquitto broker automatically publishes this message so the
        # app knows the controller went offline unexpectedly.
        client.will_set(TOPIC_SYSTEM, json.dumps({
            "status":    "offline",
            "timestamp": datetime.now().isoformat(),
            "reason":    "unexpected_disconnect"
        }), retain=True)

        # Step 4: Connect to the local Mosquitto broker
        logger.info(f"📡 Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}...")
        client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)

        # Step 5: Enter the event loop — this function blocks here forever,
        # processing incoming MQTT messages and calling our callbacks.
        logger.info("🎮 Simpson's House is ready! Open the iPad app to start controlling.")
        client.loop_forever()

    except KeyboardInterrupt:
        logger.info("⌨️  Stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        try:
            stop_garage_emergency()
        except Exception:
            pass
    finally:
        cleanup_and_exit()


if __name__ == "__main__":
    main()
