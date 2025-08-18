#!/usr/bin/env python3
"""
Simpson's House MQTT Listener and GPIO Controller with L293D Motor Driver
Handles MQTT commands from iOS Swift Playgrounds app and controls Raspberry Pi GPIO
Now includes L293D motor driver for professional DC motor control
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

# GPIO pin assignments (BCM numbering) - Simpson's House Layout with L293D
LIGHT_PIN = 17     # Living Room Light (LED + 220Ω resistor)
MOTOR_PIN1 = 27    # L293D Input1 (motor direction control)
MOTOR_PIN2 = 18    # L293D Input2 (motor direction control)
MOTOR_ENABLE = 22  # L293D Enable1 (PWM speed control)
SERVO_PIN = 23     # Front Door Servo (moved from GPIO 22)

# MQTT broker settings
BROKER_HOST = "localhost"
BROKER_PORT = 1883
KEEPALIVE   = 60

# MQTT topics matching iOS Swift Playgrounds app
TOPIC_LIGHT = "home/light"
TOPIC_FAN   = "home/fan"     # Now controls DC motor via L293D
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

# Motor control states
motor_state = {
    "running": False,
    "direction": "forward",  # "forward", "reverse", "stop"
    "speed": 75              # PWM duty cycle percentage (0-100)
}

# Global MQTT client and PWM objects
client = None
MOTOR_PWM = None
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
    """Initialize GPIO pins for Simpson's House devices with L293D motor driver."""
    logger.info("🏠 Initializing Simpson's House GPIO with L293D motor driver...")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup output pins with initial OFF state
    GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(MOTOR_PIN1, GPIO.OUT, initial=GPIO.LOW)    # L293D Input1
    GPIO.setup(MOTOR_PIN2, GPIO.OUT, initial=GPIO.LOW)    # L293D Input2
    GPIO.setup(MOTOR_ENABLE, GPIO.OUT, initial=GPIO.LOW)  # L293D Enable1
    GPIO.setup(SERVO_PIN, GPIO.OUT, initial=GPIO.LOW)
    
    # Initialize PWM for motor speed control (1kHz frequency)
    global MOTOR_PWM, SERVO_PWM
    MOTOR_PWM = GPIO.PWM(MOTOR_ENABLE, 1000)  # 1kHz for smooth motor control
    MOTOR_PWM.start(0)  # Start with 0% duty cycle (motor off)
    
    # Initialize servo PWM at 50 Hz
    SERVO_PWM = GPIO.PWM(SERVO_PIN, 50)
    SERVO_PWM.start(0)
    
    logger.info(f"💡 Light configured on GPIO {LIGHT_PIN}")
    logger.info(f"🌀 L293D Motor Driver configured:")
    logger.info(f"   - Input1 (direction): GPIO {MOTOR_PIN1}")
    logger.info(f"   - Input2 (direction): GPIO {MOTOR_PIN2}")
    logger.info(f"   - Enable1 (PWM speed): GPIO {MOTOR_ENABLE}")
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

def set_motor_direction(direction: str) -> bool:
    """
    Set L293D motor direction.
    direction: "forward", "reverse", or "stop"
    Returns True if successful, False otherwise.
    """
    try:
        if direction == "forward":
            GPIO.output(MOTOR_PIN1, GPIO.HIGH)
            GPIO.output(MOTOR_PIN2, GPIO.LOW)
            motor_state["direction"] = "forward"
            logger.info("🔄 Motor direction: FORWARD")
            
        elif direction == "reverse":
            GPIO.output(MOTOR_PIN1, GPIO.LOW)
            GPIO.output(MOTOR_PIN2, GPIO.HIGH)
            motor_state["direction"] = "reverse"
            logger.info("🔄 Motor direction: REVERSE")
            
        elif direction == "stop":
            GPIO.output(MOTOR_PIN1, GPIO.LOW)
            GPIO.output(MOTOR_PIN2, GPIO.LOW)
            motor_state["direction"] = "stop"
            logger.info("🛑 Motor direction: STOP")
            
        else:
            logger.error(f"Invalid motor direction: {direction}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Motor direction control failed: {e}")
        return False

def set_motor_speed(speed_percent: int) -> bool:
    """
    Set L293D motor speed using PWM.
    speed_percent: 0-100 (percentage of maximum speed)
    Returns True if successful, False otherwise.
    """
    try:
        if not 0 <= speed_percent <= 100:
            logger.error(f"Invalid motor speed: {speed_percent}%. Must be 0-100.")
            return False
            
        MOTOR_PWM.ChangeDutyCycle(speed_percent)
        motor_state["speed"] = speed_percent
        
        if speed_percent == 0:
            motor_state["running"] = False
            logger.info("🛑 Motor speed: 0% (STOPPED)")
        else:
            motor_state["running"] = True
            logger.info(f"⚡ Motor speed: {speed_percent}%")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Motor speed control failed: {e}")
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
        publish_system_status("online", "Simpson's House controller with L293D motor driver started")
        
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
            device_name = "DC Motor (via L293D)"
            
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
    """
    Control the DC motor via L293D driver.
    state: True = run motor forward, False = stop motor
    """
    try:
        if state:
            # Turn motor ON - run forward at configured speed
            logger.info("🌀 Starting DC motor via L293D...")
            
            # Set direction to forward
            if not set_motor_direction("forward"):
                return False
            
            # Set speed to default 75%
            if not set_motor_speed(motor_state["speed"]):
                return False
                
            logger.info(f"🌀 DC Motor: ON (Forward, {motor_state['speed']}% speed)")
            
        else:
            # Turn motor OFF
            logger.info("🛑 Stopping DC motor...")
            
            # Stop motor by setting speed to 0
            if not set_motor_speed(0):
                return False
                
            # Set direction to stop for safety
            if not set_motor_direction("stop"):
                return False
                
            logger.info("🌀 DC Motor: OFF")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Motor control error: {e}")
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
        set_motor_speed(0)
        set_motor_direction("stop")
        motor_state["running"] = False
    except Exception as e:
        logger.error(f"❌ Emergency stop failed: {e}")

def get_motor_status() -> dict:
    """Get current motor status for diagnostics."""
    return {
        "running": motor_state["running"],
        "direction": motor_state["direction"],
        "speed_percent": motor_state["speed"],
        "gpio_states": {
            "input1": GPIO.input(MOTOR_PIN1),
            "input2": GPIO.input(MOTOR_PIN2),
            "enable": GPIO.input(MOTOR_ENABLE)
        }
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
            "controller": "Simpson's House GPIO Controller with L293D",
            "motor_driver": "L293D",
            "gpio_pins": {
                "light": LIGHT_PIN,
                "motor_input1": MOTOR_PIN1,
                "motor_input2": MOTOR_PIN2,
                "motor_enable": MOTOR_ENABLE,
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
        GPIO.output(MOTOR_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_PIN2, GPIO.LOW)
        
        # Stop PWM and cleanup GPIO
        if MOTOR_PWM:
            MOTOR_PWM.stop()
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
    logger.info("🔧 Now with L293D Motor Driver Support!")
    logger.info("📺 'D'oh! Welcome to the smartest house in Springfield!'")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize GPIO
        setup_gpio()
        
        # Create and configure MQTT client
        client = mqtt.Client(client_id="simpsons_house_l293d_controller")
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
        logger.info("🎮 Simpson's House with L293D motor control ready!")
        logger.info("📱 Connect your iPhone/iPad and start controlling the house!")
        logger.info("🌀 Motor control: ON=Forward, OFF=Stop")
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
