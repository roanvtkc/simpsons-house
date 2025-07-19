#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import logging

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────

# GPIO pin assignments (BCM numbering)
LIGHT_PIN = 17
FAN_PIN   = 27
SERVO_PIN = 22

# MQTT broker settings
BROKER_HOST = "localhost"
BROKER_PORT = 1883
KEEPALIVE   = 60

# MQTT topics (matching Swift Playgrounds)
TOPIC_LIGHT = "home/light"
TOPIC_FAN   = "home/fan"
TOPIC_DOOR  = "home/door"

# ─── SETUP ───────────────────────────────────────────────────────────────────────

# Logging setup
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# GPIO initialization
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(LIGHT_PIN, GPIO.OUT)
GPIO.setup(FAN_PIN,   GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Servo PWM at 50 Hz
SERVO_PWM = GPIO.PWM(SERVO_PIN, 50)
SERVO_PWM.start(0)

def set_servo_angle(angle: int) -> None:
    """Move servo to a given angle (0–180°)."""
    duty = angle / 18 + 2
    SERVO_PWM.ChangeDutyCycle(duty)
    time.sleep(0.5)
    SERVO_PWM.ChangeDutyCycle(0)

# ─── MQTT CALLBACKS ─────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT broker")
        # Subscribe to updated topics
        client.subscribe(TOPIC_LIGHT)
        client.subscribe(TOPIC_FAN)
        client.subscribe(TOPIC_DOOR)
        logging.info(f"Subscribed to: {TOPIC_LIGHT}, {TOPIC_FAN}, {TOPIC_DOOR}")
    else:
        logging.error(f"Bad connection (rc={rc})")


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip().upper()
    logging.info(f"→ Topic: {msg.topic}, Payload: {payload}")
    
    if msg.topic == TOPIC_LIGHT:
        state = GPIO.HIGH if payload == "ON" else GPIO.LOW
        GPIO.output(LIGHT_PIN, state)
        logging.info(f"Light set to {'ON' if state==GPIO.HIGH else 'OFF'}")
    
    elif msg.topic == TOPIC_FAN:
        state = GPIO.HIGH if payload == "ON" else GPIO.LOW
        GPIO.output(FAN_PIN, state)
        logging.info(f"Fan set to {'ON' if state==GPIO.HIGH else 'OFF'}")
    
    elif msg.topic == TOPIC_DOOR:
        angle = 90 if payload == "ON" else 0
        set_servo_angle(angle)
        logging.info(f"Door servo moved to {angle}°")

# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        logging.info(f"Connecting to {BROKER_HOST}:{BROKER_PORT}")
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info("Interrupted by user, cleaning up…")
    finally:
        SERVO_PWM.stop()
        GPIO.cleanup()
        logging.info("GPIO cleaned up, exiting.")

if __name__ == "__main__":
    main()
