import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# GPIO pin assignments
LIGHT_PIN = 17
FAN_PIN = 27
SERVO_PIN = 22

# Initial setup for GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LIGHT_PIN, GPIO.OUT)
GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Servo PWM configuration
SERVO_PWM = GPIO.PWM(SERVO_PIN, 50)
SERVO_PWM.start(0)

def set_servo_angle(angle: int):
    """Move servo to specified angle."""
    duty = 2 + (angle / 18)
    SERVO_PWM.ChangeDutyCycle(duty)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("light")
    client.subscribe("fan")
    client.subscribe("door")

def on_message(client, userdata, msg):
    payload = msg.payload.decode().upper()
    print(f"Topic: {msg.topic}, Message: {payload}")

    if msg.topic == "light":
        GPIO.output(LIGHT_PIN, GPIO.HIGH if payload == "ON" else GPIO.LOW)

    elif msg.topic == "fan":
        GPIO.output(FAN_PIN, GPIO.HIGH if payload == "ON" else GPIO.LOW)

    elif msg.topic == "door":
        angle = 90 if payload == "ON" else 0
        set_servo_angle(angle)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

try:
    client.loop_forever()
finally:
    SERVO_PWM.stop()
    GPIO.cleanup()
