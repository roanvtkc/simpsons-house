#!/usr/bin/env python3
"""
Simpson's House MQTT Listener and GPIO Controller with Variable Speed Stepper Motor
Handles MQTT commands from iOS Swift Playgrounds app and controls Raspberry Pi GPIO
Uses a 28BYJ-48 stepper motor driven by a ULN2003 board with variable speed control
"""

import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import logging
import json
import signal
import sys
import threading
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

# Enhanced stepper motor state with speed control
motor_state = {
    "running": False,
    "position": 0,  # cumulative steps moved
    "current_speed": 0,  # 0-100 percentage
    "target_speed": 0,
    "direction": "forward",
    "step_delay": 0.002  # current delay between steps
}

# Global objects
client = None
SERVO_PWM = None
motor_thread = None
motor_stop_event = threading.Event()

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
    logger.info("🏠 Initializing Simpson's House GPIO with variable speed stepper motor...")
    
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

# ─── ENHANCED STEPPER MOTOR CONTROL ────────────────────────────────────────────

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

def speed_to_delay(speed_percent: int) -> float:
    """Convert speed percentage (0-100) to step delay in seconds."""
    if speed_percent <= 0:
        return 0.1  # Very slow fallback
    elif speed_percent >= 100:
        return 0.001  # Maximum speed
    else:
        # Linear mapping: 100% = 0.001s, 1% = 0.02s
        return 0.02 - (speed_percent / 100.0) * 0.019

def stepper_continuous_run():
    """Continuous stepper motor runner in separate thread."""
    global motor_state
    
    logger.info("🌀 Stepper motor thread started")
    step_index = 0
    
    while not motor_stop_event.is_set():
        try:
            if motor_state["running"] and motor_state["current_speed"] > 0:
                # Get current step pattern
                sequence = STEP_SEQUENCE if motor_state["direction"] == "forward" else list(reversed(STEP_SEQUENCE))
                pattern = sequence[step_index % len(sequence)]
                
                # Apply step pattern to GPIO pins
                for pin, value in zip(STEPPER_PINS, pattern):
                    GPIO.output(pin, value)
                
                # Wait based on current speed
                delay = motor_state["step_delay"]
                if motor_stop_event.wait(timeout=delay):
                    break  # Stop event was set
                
                # Update position and step index
                step_index = (step_index + 1) % len(sequence)
                if motor_state["direction"] == "forward":
                    motor_state["position"] += 1
                else:
                    motor_state["position"] -= 1
                    
            else:
                # Motor not running, wait a bit before checking again
                if motor_stop_event.wait(timeout=0.1):
                    break
                    
        except Exception as e:
            logger.error(f"❌ Stepper motor thread error: {e}")
            break
    
    # Ensure all pins are off when thread exits
    stop_stepper_immediately()
    logger.info("🛑 Stepper motor thread stopped")

def start_stepper_thread():
    """Start the stepper motor control thread."""
    global motor_thread
    if motor_thread is None or not motor_thread.is_alive():
        motor_stop_event.clear()
        motor_thread = threading.Thread(target=stepper_continuous_run, daemon=True)
        motor_thread.start()
        logger.info("🚀 Stepper motor control thread started")

def stop_stepper_immediately():
    """Immediately stop stepper motor and turn off all pins."""
    for pin in STEPPER_PINS:
        GPIO.output(pin, GPIO.LOW)
    motor_state["running"] = False
    motor_state["current_speed"] = 0

def set_stepper_speed(speed_percent: int) -> bool:
    """Set stepper motor speed (0-100%)."""
    try:
        # Validate speed
        if not 0 <= speed_percent <= 100:
            logger.error(f"❌ Invalid speed: {speed_percent}%. Must be 0-100.")
            return False
        
        logger.info(f"🌀 Setting stepper speed to {speed_percent}%")
        
        # Update motor state
        motor_state["target_speed"] = speed_percent
        motor_state["current_speed"] = speed_percent
        motor_state["step_delay"] = speed_to_delay(speed_percent)
        
        if speed_percent == 0:
            # Stop motor
            motor_state["running"] = False
            stop_stepper_immediately()
            logger.info("🛑 Stepper motor stopped")
        else:
            # Start or update motor speed
            motor_state["running"] = True
            start_stepper_thread()
            logger.info(f"🌀 Stepper motor running at {speed_percent}% speed (delay: {motor_state['step_delay']:.4f}s)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Stepper speed control error: {e}")
        return False

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
        publish_system_status("online", "Simpson's House controller with variable speed stepper motor started")
        
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
            else:
                logger.warning(f"⚠️  Invalid light command '{payload}' for {topic}")
                publish_error(topic, f"Invalid light command: {payload}")
                return
            
        elif topic == TOPIC_FAN:
            success = control_motor_with_speed(payload)
            device_name = "Stepper Motor"
            
        elif topic == TOPIC_DOOR:
            if payload.upper() in ["ON", "OFF"]:
                command_state = (payload.upper() == "ON")
                success = control_door(command_state)
                device_name = "Front Door"
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
            
            # Update device states appropriately
            if topic == TOPIC_LIGHT:
                device_states[device_key] = (payload.upper() == "ON")
            elif topic == TOPIC_FAN:
                device_states[device_key] = motor_state["running"]
            elif topic == TOPIC_DOOR:
                device_states[device_key] = (payload.upper() == "ON")
            
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

def control_motor_with_speed(command: str) -> bool:
    """
    Control the stepper motor with speed commands.
    Accepts: ON, OFF, SPEED:X (where X is 0-100)
    """
    try:
        command = command.upper().strip()
        logger.info(f"🌀 Processing stepper motor command: '{command}'")
        
        if command == "OFF":
            logger.info("🛑 Stopping stepper motor...")
            return set_stepper_speed(0)
            
        elif command == "ON":
            logger.info("🌀 Starting stepper motor at default speed (50%)...")
            return set_stepper_speed(50)
            
        elif command.startswith("SPEED:"):
            # Parse speed value
            try:
                speed_str = command[6:]  # Remove "SPEED:" prefix
                speed_value = int(speed_str)
                logger.info(f"🌀 Setting stepper motor to {speed_value}% speed...")
                return set_stepper_speed(speed_value)
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

# ─── MOTOR CONTROL UTILITY FUNCTIONS ───────────────────────────────────────────

def stop_motor_emergency():
    """Emergency stop for motor - cuts power immediately."""
    try:
        logger.warning("🚨 EMERGENCY MOTOR STOP")
        motor_stop_event.set()
        stop_stepper_immediately()
    except Exception as e:
        logger.error(f"❌ Emergency stop failed: {e}")

def get_motor_status() -> dict:
    """Get current stepper motor status for diagnostics."""
    return {
        "running": motor_state["running"],
        "current_speed": motor_state["current_speed"],
        "target_speed": motor_state["target_speed"],
        "position": motor_state["position"],
        "direction": motor_state["direction"],
        "step_delay": motor_state["step_delay"],
        "gpio_states": {f"pin{idx+1}": GPIO.input(pin) for idx, pin in enumerate(STEPPER_PINS)},
        "thread_alive": motor_thread.is_alive() if motor_thread else False
    }

# ─── MQTT PUBLISHING FUNCTIONS ─────────────────────────────────────────────────

def publish_device_status(device: str, status: bool):
    """Publish device status update to MQTT for iOS app feedback."""
    try:
        status_msg = "ON" if status else "OFF"
        status_topic = f"home/{device}/status"
        
        # Publish individual device status
        client.publish(status_topic, status_msg, retain=True)
        
        # Include detailed motor diagnostics for fan status
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
            "version": "3.2",
            "controller": "Simpson's House GPIO Controller with Variable Speed Stepper Motor",
            "motor_driver": "ULN2003",
            "motor_features": "Variable speed 0-100%",
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
        
        # Wait for motor thread to finish
        if motor_thread and motor_thread.is_alive():
            motor_stop_event.set()
            motor_thread.join(timeout=2.0)
        
        # Turn off all devices safely
        logger.info("🔌 Turning off all devices...")
        GPIO.output(LIGHT_PIN, GPIO.LOW)
        stop_stepper_immediately()

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
    
    logger.info("🏠 Starting Simpson's House Smart Home Controller v3.2")
    logger.info("🔧 Now with VARIABLE SPEED stepper motor support!")
    logger.info("📺 'D'oh! Welcome to the smartest house in Springfield!'")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize GPIO
        setup_gpio()
        
        # Create and configure MQTT client
        client = mqtt.Client(client_id="simpsons_house_variable_speed_controller")
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
        logger.info("🎮 Simpson's House with variable speed stepper motor control ready!")
        logger.info("📱 Connect your iPhone/iPad and start controlling the house!")
        logger.info("🌀 Stepper control commands:")
        logger.info("   • OFF - Stop motor")
        logger.info("   • ON - Start at 50% speed")
        logger.info("   • SPEED:X - Set speed to X% (0-100)")
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
