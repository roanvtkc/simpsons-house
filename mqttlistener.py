#!/usr/bin/env python3
"""
Simpson's House MQTT Listener and GPIO Controller with Stepper Motor
Handles MQTT commands from iOS Swift Playgrounds app and controls Raspberry Pi GPIO
Uses a 28BYJ-48 stepper motor driven by a ULN2003 board
"""

import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import logging
import json
import signal
import sys
from datetime import datetime

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────

# GPIO pin assignments (BCM numbering)
LIGHT_PIN = 17     # Living Room Light (LED + 220Ω resistor)
STEPPER_PINS = [27, 18, 22, 24]  # ULN2003 IN1-IN4 for stepper motor
SERVO_PIN = 23     # Front Door Servo

# MQTT broker settings
BROKER_HOST = "localhost"
BROKER_PORT = 1883
KEEPALIVE   = 60

# MQTT topics matching iOS Swift Playgrounds app
TOPIC_LIGHT = "home/light"
TOPIC_FAN   = "home/fan"     # Controls stepper motor via ULN2003 driver
TOPIC_DOOR  = "home/door"

# Status feedback topics for iOS app
TOPIC_STATUS = "home/status"
TOPIC_SYSTEM = "home/system"

# Device states tracking
device_states = {
    "light": False,
    "fan": False,
    "door": False
}

# Stepper motor state
motor_state = {
    "running": False,
    "position": 0  # cumulative steps moved
}

# Global MQTT client and servo PWM object
client = None
SERVO_PWM = None

# ─── LOGGING SETUP ──────────────────────────────────────────────────────────────

# Configure logging for systemd journal output
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] Simpson's House: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ─── GPIO INITIALIZATION ───────────────────────────────────────────────────────

def setup_gpio():
    """Initialize GPIO pins for Simpson's House devices with stepper motor."""
    logger.info("🏠 Initializing Simpson's House GPIO with stepper motor...")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup output pins with initial OFF state
    GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)
    for pin in STEPPER_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SERVO_PIN, GPIO.OUT, initial=GPIO.LOW)

    # Initialize servo PWM at 50 Hz
    global SERVO_PWM
    SERVO_PWM = GPIO.PWM(SERVO_PIN, 50)
    SERVO_PWM.start(0)

    logger.info(f"💡 Light configured on GPIO {LIGHT_PIN}")
    logger.info(f"🌀 Stepper motor configured on pins: {STEPPER_PINS}")
    logger.info(f"🚪 Door servo configured on GPIO {SERVO_PIN}")

def set_servo_angle(angle: int) -> bool:
    """
    Move servo to specified angle (0-180 degrees).
    Returns True if successful, False otherwise.
    """
    try:
        if not 0 <= angle <= 180:
            logger.error(f"Invalid servo angle: {angle}. Must be 0-180.")
            return False
            
        # Convert angle to duty cycle (2-12% duty cycle for 0-180 degrees)
        duty = (angle / 180.0) * 10 + 2
        SERVO_PWM.ChangeDutyCycle(duty)
        time.sleep(0.8)  # Give servo time to move
        SERVO_PWM.ChangeDutyCycle(0)  # Stop PWM to prevent jitter
        
        logger.info(f"🚪 Door servo moved to {angle}°")
        return True
        
    except Exception as e:
        logger.error(f"❌ Servo control failed: {e}")
        return False

STEP_SEQUENCE = [
    [1, 0, 0, 1],
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1]
]

def stepper_step(sequence, steps, delay=0.002):
    """Run the stepper motor for given steps using provided sequence."""
    for _ in range(steps):
        for pattern in sequence:
            for pin, value in zip(STEPPER_PINS, pattern):
                GPIO.output(pin, value)
            time.sleep(delay)
    stop_stepper()

def rotate_stepper(direction: str, steps: int = 512):
    """Rotate stepper motor in specified direction for steps."""
    seq = STEP_SEQUENCE if direction == "forward" else list(reversed(STEP_SEQUENCE))
    stepper_step(seq, steps)
    motor_state["position"] += steps if direction == "forward" else -steps

def stop_stepper():
    for pin in STEPPER_PINS:
        GPIO.output(pin, GPIO.LOW)
    motor_state["running"] = False

# ─── MQTT EVENT HANDLERS ───────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    """Called when MQTT client connects to broker."""
    if rc == 0:
        logger.info("✅ Connected to Simpson's House MQTT broker")
        
        # Subscribe to device control topics
        topics = [TOPIC_LIGHT, TOPIC_FAN, TOPIC_DOOR]
        for topic in topics:
            client.subscribe(topic)
            logger.info(f"📡 Subscribed to: {topic}")
        
        # Publish initial system status
        publish_system_status("online", "Simpson's House controller with stepper motor started")
        
        # Publish initial device states
        for device, state in device_states.items():
            publish_device_status(device, state)
            
    else:
        logger.error(f"❌ MQTT connection failed (code={rc})")
        logger.error(f"   Error: {get_mqtt_error_message(rc)}")

def on_disconnect(client, userdata, rc):
    """Called when MQTT client disconnects from broker."""
    if rc != 0:
        logger.warning(f"⚠️  Unexpected MQTT disconnection (code={rc})")
    else:
        logger.info("📡 MQTT disconnected cleanly")

def on_message(client, userdata, msg):
    """
    Handle incoming MQTT messages from iOS app.
    Processes device control commands and updates GPIO accordingly.
    """
    try:
        topic = msg.topic
        payload = msg.payload.decode().strip().upper()
        
        logger.info(f"📨 Received command: {topic} → {payload}")
        
        # Validate command
        if payload not in ["ON", "OFF"]:
            logger.warning(f"⚠️  Invalid command '{payload}' for {topic}")
            publish_error(topic, f"Invalid command: {payload}")
            return
        
        command_state = (payload == "ON")
        success = False
        device_name = ""
        
        # Execute command based on topic
        if topic == TOPIC_LIGHT:
            success = control_light(command_state)
            device_name = "Living Room Light"
            
        elif topic == TOPIC_FAN:
            success = control_motor(command_state)
            device_name = "Stepper Motor"
            
        elif topic == TOPIC_DOOR:
            success = control_door(command_state)
            device_name = "Front Door"
            
        else:
            logger.warning(f"⚠️  Unknown topic: {topic}")
            return
        
        # Update device state and publish status
        if success:
            device_key = topic.split('/')[-1]  # Extract device name from topic
            device_states[device_key] = command_state
            
            publish_device_status(device_key, command_state)
            logger.info(f"✅ {device_name} successfully turned {'ON' if command_state else 'OFF'}")
        else:
            logger.error(f"❌ Failed to control {device_name}")
            publish_error(topic, f"Device control failed")
            
    except Exception as e:
        logger.error(f"❌ Message handling error: {e}")
        publish_error(msg.topic, f"Processing error: {str(e)}")

# ─── DEVICE CONTROL FUNCTIONS ──────────────────────────────────────────────────

def control_light(state: bool) -> bool:
    """Control the living room light (GPIO 17)."""
    try:
        gpio_state = GPIO.HIGH if state else GPIO.LOW
        GPIO.output(LIGHT_PIN, gpio_state)
        logger.info(f"💡 Living Room Light: {'ON' if state else 'OFF'}")
        return True
    except Exception as e:
        logger.error(f"❌ Light control error: {e}")
        return False

def control_motor(state: bool) -> bool:
    """Control the stepper motor via ULN2003 driver."""
    try:
        if state:
            logger.info("🌀 Rotating stepper motor forward...")
            motor_state["running"] = True
            rotate_stepper("forward", 512)
            motor_state["running"] = False
        else:
            logger.info("🛑 Stopping stepper motor...")
            stop_stepper()
        return True
    except Exception as e:
        logger.error(f"❌ Stepper motor control error: {e}")
        return False

def control_door(state: bool) -> bool:
    """Control the front door servo (GPIO 23)."""
    try:
        # Open = 90 degrees, Closed = 0 degrees
        angle = 90 if state else 0
        success = set_servo_angle(angle)
        if success:
            action = "OPENED" if state else "CLOSED"
            logger.info(f"🚪 Front Door: {action}")
        return success
    except Exception as e:
        logger.error(f"❌ Door control error: {e}")
        return False

# ─── MOTOR CONTROL UTILITY FUNCTIONS ───────────────────────────────────────────

def stop_motor_emergency():
    """Emergency stop for motor - cuts power immediately."""
    try:
        logger.warning("🚨 EMERGENCY MOTOR STOP")
        stop_stepper()
    except Exception as e:
        logger.error(f"❌ Emergency stop failed: {e}")

def get_motor_status() -> dict:
    """Get current stepper motor status for diagnostics."""
    return {
        "running": motor_state["running"],
        "position": motor_state["position"],
        "gpio_states": {f"pin{idx+1}": GPIO.input(pin) for idx, pin in enumerate(STEPPER_PINS)}
    }

# ─── MQTT PUBLISHING FUNCTIONS ─────────────────────────────────────────────────

def publish_device_status(device: str, status: bool):
    """Publish device status update to MQTT for iOS app feedback."""
    try:
        status_msg = "ON" if status else "OFF"
        status_topic = f"home/{device}/status"
        
        # Publish individual device status
        client.publish(status_topic, status_msg, retain=True)
        
        # Include motor diagnostics for fan status
        if device == "fan":
            motor_status = get_motor_status()
            motor_status_topic = f"home/{device}/motor_status"
            client.publish(motor_status_topic, json.dumps(motor_status), retain=True)
        
        # Publish comprehensive system status
        system_status = {
            "timestamp": datetime.now().isoformat(),
            "devices": device_states.copy(),
            "motor": motor_state.copy(),
            "controller": "online"
        }
        client.publish(TOPIC_STATUS, json.dumps(system_status), retain=True)
        
    except Exception as e:
        logger.error(f"❌ Status publishing error: {e}")

def publish_system_status(status: str, message: str = ""):
    """Publish overall system status."""
    try:
        system_info = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "version": "3.1",
            "controller": "Simpson's House GPIO Controller with Stepper Motor",
            "motor_driver": "ULN2003",
            "gpio_pins": {
                "light": LIGHT_PIN,
                "stepper": STEPPER_PINS,
                "servo": SERVO_PIN
            }
        }
        client.publish(TOPIC_SYSTEM, json.dumps(system_info), retain=True)
    except Exception as e:
        logger.error(f"❌ System status publishing error: {e}")

def publish_error(topic: str, error_msg: str):
    """Publish error message for iOS app debugging."""
    try:
        error_topic = f"{topic}/error"
        error_info = {
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "motor_status": get_motor_status() if "fan" in topic else None
        }
        client.publish(error_topic, json.dumps(error_info))
    except Exception as e:
        logger.error(f"❌ Error publishing failed: {e}")

# ─── UTILITY FUNCTIONS ─────────────────────────────────────────────────────────

def get_mqtt_error_message(rc: int) -> str:
    """Convert MQTT return code to human-readable message."""
    error_messages = {
        1: "Incorrect protocol version",
        2: "Invalid client identifier", 
        3: "Server unavailable",
        4: "Bad username or password",
        5: "Not authorized"
    }
    return error_messages.get(rc, f"Unknown error (code {rc})")

# ─── SIGNAL HANDLING AND CLEANUP ──────────────────────────────────────────────

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"🛑 Received signal {signum}, shutting down Simpson's House...")
    cleanup_and_exit()

def cleanup_and_exit():
    """Perform clean shutdown of all systems."""
    logger.info("🧹 Cleaning up Simpson's House systems...")
    
    try:
        # Emergency stop motor first
        logger.info("🚨 Emergency stopping motor...")
        stop_motor_emergency()
        
        # Turn off all devices safely
        logger.info("🔌 Turning off all devices...")
        GPIO.output(LIGHT_PIN, GPIO.LOW)
        stop_stepper()

        # Stop PWM and cleanup GPIO
        if SERVO_PWM:
            SERVO_PWM.stop()
        GPIO.cleanup()
        logger.info("✅ GPIO cleaned up successfully")
        
    except Exception as e:
        logger.error(f"❌ GPIO cleanup error: {e}")
    
    try:
        # Publish offline status
        if client and client.is_connected():
            publish_system_status("offline", "Controller shutting down")
            client.disconnect()
            logger.info("📡 MQTT disconnected")
            
    except Exception as e:
        logger.error(f"❌ MQTT cleanup error: {e}")
    
    logger.info("👋 Simpson's House controller stopped. Goodbye!")
    sys.exit(0)

# ─── MAIN FUNCTION ─────────────────────────────────────────────────────────────

def main():
    """Main function to run Simpson's House MQTT listener."""
    global client
    
    logger.info("🏠 Starting Simpson's House Smart Home Controller v3.1")
    logger.info("🔧 Now with stepper motor support!")
    logger.info("📺 'D'oh! Welcome to the smartest house in Springfield!'")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize GPIO
        setup_gpio()
        
        # Create and configure MQTT client
        client = mqtt.Client(client_id="simpsons_house_stepper_controller")
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # Set last will message (published if connection lost unexpectedly)
        client.will_set(TOPIC_SYSTEM, json.dumps({
            "status": "offline",
            "timestamp": datetime.now().isoformat(),
            "reason": "unexpected_disconnect",
            "motor_emergency_stopped": True
        }), retain=True)
        
        # Connect to MQTT broker
        logger.info(f"📡 Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
        client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        
        # Start MQTT message loop
        logger.info("🎮 Simpson's House with stepper motor control ready!")
        logger.info("📱 Connect your iPhone/iPad and start controlling the house!")
        logger.info("🌀 Stepper control: ON=Forward rotation, OFF=Stop")
        client.loop_forever()
        
    except KeyboardInterrupt:
        logger.info("⌨️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error("💥 Simpson's House controller crashed!")
        # Emergency stop motor on crash
        try:
            stop_motor_emergency()
        except:
            pass
    finally:
        cleanup_and_exit()

if __name__ == "__main__":
    main()
