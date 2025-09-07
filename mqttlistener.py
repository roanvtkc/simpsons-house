#!/usr/bin/env python3
"""
Simpson's House MQTT Listener and GPIO Controller with Simplified Stepper Motor
Handles MQTT commands from iOS Swift Playgrounds app and controls Raspberry Pi GPIO
Uses a 28BYJ-48 stepper motor driven by a ULN2003 board with simple speed control
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
    "position": 0,  # cumulative steps moved
    "current_speed": 0,  # 0-100 percentage
    "last_command": "OFF"
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

# ─── SIMPLIFIED STEPPER MOTOR CONTROL ──────────────────────────────────────────

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
    motor_state["running"] = False
    motor_state["current_speed"] = 0
    logger.info("🛑 Stepper motor stopped")

def run_stepper_steps(steps: int, delay: float, speed_percent: int):
    """Run stepper motor for specified steps with given delay."""
    logger.info(f"🌀 Running stepper motor: {steps} steps, {delay:.4f}s delay, {speed_percent}% speed")
    
    motor_state["running"] = True
    motor_state["current_speed"] = speed_percent
    
    try:
        for step in range(steps):
            # Get step pattern
            pattern = STEP_SEQUENCE[step % len(STEP_SEQUENCE)]
            
            # Apply pattern to GPIO pins
            for pin, value in zip(STEPPER_PINS, pattern):
                GPIO.output(pin, value)
            
            # Wait between steps
            time.sleep(delay)
            
            # Update position
            motor_state["position"] += 1
        
        # Turn off all pins after completion
        stop_stepper()
        logger.info(f"✅ Stepper motor completed {steps} steps")
        
    except Exception as e:
        logger.error(f"❌ Stepper motor error: {e}")
        stop_stepper()

def speed_to_steps_and_delay(speed_percent: int):
    """Convert speed percentage to steps and delay."""
    if speed_percent <= 0:
        return 0, 0.002
    elif speed_percent <= 25:
        return 128, 0.004   # Quarter turn, slow
    elif speed_percent <= 50:
        return 256, 0.003   # Half turn, medium
    elif speed_percent <= 75:
        return 384, 0.002   # Three quarter turn, fast
    else:
        return 512, 0.002   # Full turn, fastest

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
        publish_system_status("online", "Simpson's House controller with simplified stepper motor started")
        
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
            
        elif topic == TOPIC_FAN:
            success = control_motor_simplified(payload)
            device_name = "Stepper Motor"
            device_states["fan"] = motor_state["running"]
            
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

def control_motor_simplified(command: str) -> bool:
    """
    Simplified stepper motor control that works like the test script.
    Accepts: ON, OFF, SPEED:X (where X is 0-100)
    """
    try:
        command = command.upper().strip()
        logger.info(f"🌀 Processing stepper motor command: '{command}'")
        
        motor_state["last_command"] = command
        
        if command == "OFF":
            logger.info("🛑 Stopping stepper motor...")
            stop_stepper()
            return True
            
        elif command == "ON":
            logger.info("🌀 Starting stepper motor at default speed (50%)...")
            steps, delay = speed_to_steps_and_delay(50)
            run_stepper_steps(steps, delay, 50)
            return True
            
        elif command.startswith("SPEED:"):
            # Parse speed value
            try:
                speed_str = command[6:]  # Remove "SPEED:" prefix
                speed_value = int(speed_str)
                
                if not 0 <= speed_value <= 100:
                    logger.error(f"❌ Speed value {speed_value} out of range (0-100)")
                    return False
                
                if speed_value == 0:
                    logger.info("🛑 Speed 0 - stopping motor...")
                    stop_stepper()
                    return True
                else:
                    logger.info(f"🌀 Setting stepper motor to {speed_value}% speed...")
                    steps, delay = speed_to_steps_and_delay(speed_value)
                    run_stepper_steps(steps, delay, speed_value)
                    return True
                    
            except ValueError:
                logger.error(f"❌ Invalid speed value in command: '{command}'. Expected SPEED:X where X is 0-100")
                return False
        else:
            logger.warning(f"⚠️  Unknown stepper motor command: '{command}'. Valid commands: ON, OFF, SPEED:X")
            return False
            
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

# ─── MOTOR STATUS FUNCTIONS ────────────────────────────────────────────────────

def get_motor_status() -> dict:
    """Get current stepper motor status for diagnostics."""
    return {
        "running": motor_state["running"],
        "current_speed": motor_state["current_speed"],
        "position": motor_state["position"],
        "last_command": motor_state["last_command"],
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
            logger.info(f"📊 Motor status published: Speed={motor_status['current_speed']}%, Running={motor_status['running']}")
        
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
            "version": "3.3",
            "controller": "Simpson's House GPIO Controller with Simplified Stepper Motor",
            "motor_driver": "ULN2003",
            "motor_control": "Non-threaded, synchronous control",
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
        # Stop motor immediately
        logger.info("🚨 Stopping motor...")
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
    
    logger.info("🏠 Starting Simpson's House Smart Home Controller v3.3")
    logger.info("🔧 Now with simplified, reliable stepper motor control!")
    logger.info("📺 'D'oh! Welcome to the smartest house in Springfield!'")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize GPIO
        setup_gpio()
        
        # Create and configure MQTT client
        client = mqtt.Client(client_id="simpsons_house_simplified_controller")
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # Set last will message (published if connection lost unexpectedly)
        client.will_set(TOPIC_SYSTEM, json.dumps({
            "status": "offline",
            "timestamp": datetime.now().isoformat(),
            "reason": "unexpected_disconnect",
            "motor_stopped": True
        }), retain=True)
        
        # Connect to MQTT broker
        logger.info(f"📡 Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
        client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        
        # Start MQTT message loop with motor stepping
        logger.info("🎮 Simpson's House with continuous stepper motor control ready!")
        logger.info("📱 Connect your iPhone/iPad and start controlling the house!")
        logger.info("🌀 Stepper control commands:")
        logger.info("   • OFF - Stop motor")
        logger.info("   • ON - Run continuously at 50% speed")
        logger.info("   • SPEED:X - Run continuously at X% speed (0-100)")
        
        # Non-blocking loop that can handle MQTT and motor stepping
        while True:
            # Process MQTT messages with short timeout
            client.loop(timeout=0.001)  # 1ms timeout
            
            # Step motor if needed
            step_motor_if_needed()
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.0001)  # 0.1ms delay
        
    except KeyboardInterrupt:
        logger.info("⌨️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error("💥 Simpson's House controller crashed!")
        # Emergency stop motor on crash
        try:
            stop_stepper()
        except:
            pass
    finally:
        cleanup_and_exit()

if __name__ == "__main__":
    main()
