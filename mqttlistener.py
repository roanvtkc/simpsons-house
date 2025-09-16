#!/usr/bin/env python3
"""
Simpson's House MQTT Listener and GPIO Controller with Garage Door Opener
Handles MQTT commands from iOS Swift Playgrounds app and controls Raspberry Pi GPIO
Uses a 28BYJ-48 stepper motor driven by a ULN2003 board as a garage door opener
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

# Garage Door Configuration
GARAGE_DOOR_REVOLUTIONS = 3  # ← CHANGE THIS TO ADJUST GARAGE DOOR TRAVEL
STEPS_PER_REVOLUTION = 512   # 28BYJ-48 stepper motor steps per revolution
GARAGE_DOOR_SPEED = 0.002    # Delay between steps (smaller = faster)

# MQTT broker settings
BROKER_HOST = "localhost"
BROKER_PORT = 1883
KEEPALIVE   = 60

# MQTT topics matching iOS Swift Playgrounds app
TOPIC_LIGHT = "home/light"
TOPIC_GARAGE = "home/garage"  # Controls garage door stepper motor
TOPIC_DOOR = "home/door"      # Front door servo

# Status feedback topics for iOS app
TOPIC_STATUS = "home/status"
TOPIC_SYSTEM = "home/system"

# Device states tracking
device_states = {
    "light": False,
    "garage": False,  # False = closed, True = open
    "door": False
}

# Garage door state
garage_state = {
    "position": "closed",  # "closed", "opening", "open", "closing"
    "step_position": 0,    # Current step position
    "total_steps": GARAGE_DOOR_REVOLUTIONS * STEPS_PER_REVOLUTION
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
    """Initialize GPIO pins for Simpson's House devices with garage door opener."""
    logger.info("🏠 Initializing Simpson's House GPIO with garage door opener...")
    
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
    logger.info(f"🏠 Garage door stepper motor configured on pins: {STEPPER_PINS}")
    logger.info(f"🚪 Front door servo configured on GPIO {SERVO_PIN}")
    logger.info(f"⚙️  Garage door: {GARAGE_DOOR_REVOLUTIONS} revolutions = {garage_state['total_steps']} steps")

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
        
        logger.info(f"🚪 Front door servo moved to {angle}°")
        return True
        
    except Exception as e:
        logger.error(f"❌ Servo control failed: {e}")
        return False

# ─── GARAGE DOOR STEPPER MOTOR CONTROL ─────────────────────────────────────────

# Step sequence matching your working stepper_test.py
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

def stop_stepper():
    """Stop stepper motor and turn off all pins."""
    for pin in STEPPER_PINS:
        GPIO.output(pin, GPIO.LOW)
    logger.info("🛑 Garage door stepper motor stopped")

def run_garage_door_steps(steps: int, direction: str):
    """Run garage door stepper motor for specified steps in given direction."""
    logger.info(f"🏠 Moving garage door {direction}: {steps} steps")
    
    # Choose step sequence direction
    sequence = STEP_SEQUENCE if direction == "opening" else list(reversed(STEP_SEQUENCE))
    
    try:
        for step in range(steps):
            # Get step pattern
            pattern = sequence[step % len(sequence)]
            
            # Apply pattern to GPIO pins
            for pin, value in zip(STEPPER_PINS, pattern):
                GPIO.output(pin, value)
            
            # Wait between steps
            time.sleep(GARAGE_DOOR_SPEED)
            
            # Update position
            if direction == "opening":
                garage_state["step_position"] += 1
            else:
                garage_state["step_position"] -= 1
        
        # Turn off all pins after completion
        stop_stepper()
        logger.info(f"✅ Garage door {direction} completed {steps} steps")
        
    except Exception as e:
        logger.error(f"❌ Garage door stepper motor error: {e}")
        stop_stepper()

def open_garage_door():
    """Open the garage door completely."""
    if garage_state["position"] == "open":
        logger.info("🏠 Garage door is already open")
        return True
    
    logger.info(f"🏠 Opening garage door ({GARAGE_DOOR_REVOLUTIONS} revolutions)...")
    garage_state["position"] = "opening"
    
    # Calculate steps needed to fully open
    steps_to_open = garage_state["total_steps"] - garage_state["step_position"]
    
    if steps_to_open > 0:
        run_garage_door_steps(steps_to_open, "opening")
    
    garage_state["position"] = "open"
    garage_state["step_position"] = garage_state["total_steps"]
    logger.info("🏠 Garage door is now OPEN")
    return True

def close_garage_door():
    """Close the garage door completely."""
    if garage_state["position"] == "closed":
        logger.info("🏠 Garage door is already closed")
        return True
    
    logger.info(f"🏠 Closing garage door ({GARAGE_DOOR_REVOLUTIONS} revolutions)...")
    garage_state["position"] = "closing"
    
    # Calculate steps needed to fully close
    steps_to_close = garage_state["step_position"]
    
    if steps_to_close > 0:
        run_garage_door_steps(steps_to_close, "closing")
    
    garage_state["position"] = "closed"
    garage_state["step_position"] = 0
    logger.info("🏠 Garage door is now CLOSED")
    return True

# ─── MQTT EVENT HANDLERS ───────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    """Called when MQTT client connects to broker."""
    if rc == 0:
        logger.info("✅ Connected to Simpson's House MQTT broker")
        
        # Subscribe to device control topics
        topics = [TOPIC_LIGHT, TOPIC_GARAGE, TOPIC_DOOR]
        for topic in topics:
            client.subscribe(topic)
            logger.info(f"📡 Subscribed to: {topic}")
        
        # Publish initial system status
        publish_system_status("online", "Simpson's House controller with garage door opener started")
        
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
        payload = msg.payload.decode().strip()
        
        logger.info(f"📨 Received MQTT message: {topic} → '{payload}'")
        
        success = False
        device_name = ""
        
        # Execute command based on topic
        if topic == TOPIC_LIGHT:
            if payload.upper() in ["ON", "OFF"]:
                command_state = (payload.upper() == "ON")
                success = control_light(command_state)
                device_name = "Living Room Light"
                device_states["light"] = command_state
            else:
                logger.warning(f"⚠️  Invalid light command '{payload}' for {topic}")
                publish_error(topic, f"Invalid light command: {payload}")
                return
            
        elif topic == TOPIC_GARAGE:
            success = control_garage_door(payload)
            device_name = "Garage Door"
            device_states["garage"] = (garage_state["position"] == "open")
            
        elif topic == TOPIC_DOOR:
            if payload.upper() in ["ON", "OFF"]:
                command_state = (payload.upper() == "ON")
                success = control_door(command_state)
                device_name = "Front Door"
                device_states["door"] = command_state
            else:
                logger.warning(f"⚠️  Invalid door command '{payload}' for {topic}")
                publish_error(topic, f"Invalid door command: {payload}")
                return
            
        else:
            logger.warning(f"⚠️  Unknown topic: {topic}")
            return
        
        # Update device state and publish status
        if success:
            device_key = topic.split('/')[-1]  # Extract device name from topic
            publish_device_status(device_key, device_states[device_key])
            logger.info(f"✅ {device_name} command '{payload}' executed successfully")
        else:
            logger.error(f"❌ Failed to control {device_name} with command '{payload}'")
            publish_error(topic, f"Device control failed for command: {payload}")
            
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

def control_garage_door(command: str) -> bool:
    """
    Control the garage door stepper motor.
    Accepts: OPEN, CLOSE
    """
    try:
        command = command.upper().strip()
        logger.info(f"🏠 Processing garage door command: '{command}'")
        
        if command == "OPEN":
            return open_garage_door()
        elif command == "CLOSE":
            return close_garage_door()
        else:
            logger.warning(f"⚠️  Unknown garage door command: '{command}'. Valid commands: OPEN, CLOSE")
            return False
            
    except Exception as e:
        logger.error(f"❌ Garage door control error: {e}")
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

# ─── STATUS FUNCTIONS ──────────────────────────────────────────────────────────

def get_garage_status() -> dict:
    """Get current garage door status for diagnostics."""
    return {
        "position": garage_state["position"],
        "step_position": garage_state["step_position"],
        "total_steps": garage_state["total_steps"],
        "revolutions": GARAGE_DOOR_REVOLUTIONS,
        "percentage_open": round((garage_state["step_position"] / garage_state["total_steps"]) * 100, 1),
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
        
        # Include garage diagnostics for garage status
        if device == "garage":
            garage_status = get_garage_status()
            garage_status_topic = f"home/{device}/garage_status"
            client.publish(garage_status_topic, json.dumps(garage_status), retain=True)
            logger.info(f"📊 Garage status published: {garage_status['position']} ({garage_status['percentage_open']}% open)")
        
        # Publish comprehensive system status
        system_status = {
            "timestamp": datetime.now().isoformat(),
            "devices": device_states.copy(),
            "garage": garage_state.copy(),
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
            "version": "3.4",
            "controller": "Simpson's House GPIO Controller with Garage Door Opener",
            "motor_driver": "ULN2003",
            "garage_config": {
                "revolutions": GARAGE_DOOR_REVOLUTIONS,
                "total_steps": garage_state["total_steps"],
                "speed": GARAGE_DOOR_SPEED
            },
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
            "garage_status": get_garage_status() if "garage" in topic else None
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
        # Stop garage door motor
        logger.info("🚨 Stopping garage door motor...")
        stop_stepper()
        
        # Turn off all devices safely
        logger.info("🔌 Turning off all devices...")
        GPIO.output(LIGHT_PIN, GPIO.LOW)

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
    
    logger.info("🏠 Starting Simpson's House Smart Home Controller v3.4")
    logger.info("🏠 Now with garage door opener control!")
    logger.info("📺 'D'oh! Welcome to the smartest house in Springfield!'")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize GPIO
        setup_gpio()
        
        # Create and configure MQTT client
        client = mqtt.Client(client_id="simpsons_house_garage_controller")
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # Set last will message (published if connection lost unexpectedly)
        client.will_set(TOPIC_SYSTEM, json.dumps({
            "status": "offline",
            "timestamp": datetime.now().isoformat(),
            "reason": "unexpected_disconnect",
            "garage_stopped": True
        }), retain=True)
        
        # Connect to MQTT broker
        logger.info(f"📡 Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
        client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        
        # Start MQTT message loop
        logger.info("🎮 Simpson's House with garage door opener ready!")
        logger.info("📱 Connect your iPhone/iPad and start controlling the house!")
        logger.info("🏠 Garage door commands:")
        logger.info("   • OPEN - Open garage door completely")
        logger.info("   • CLOSE - Close garage door completely")
        logger.info(f"⚙️  Configured for {GARAGE_DOOR_REVOLUTIONS} revolutions ({garage_state['total_steps']} steps)")
        client.loop_forever()
        
    except KeyboardInterrupt:
        logger.info("⌨️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error("💥 Simpson's House controller crashed!")
        # Emergency stop garage door on crash
        try:
            stop_stepper()
        except:
            pass
    finally:
        cleanup_and_exit()

if __name__ == "__main__":
    main()
