#!/bin/bash

set -e

# Ensure the TKC Wireless CA certificate is installed so HTTPS downloads work
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/install_ca.sh"

# Install required packages
sudo apt update
sudo apt install -y git python3-venv mosquitto

# Clone the repo if needed
if [ ! -f mqttbridge.py ]; then
    git clone https://github.com/roanvtkc/simpsons-house.git
    cd simpsons-house
fi

# Create the Python virtual environment
if [ ! -d mqttenv ]; then
    python3 -m venv mqttenv
fi
source mqttenv/bin/activate
pip install --upgrade pip
pip install flask paho-mqtt RPi.GPIO

# Enable and start the MQTT broker
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Launch bridge and listener in the background
nohup python mqttbridge.py &>/tmp/mqttbridge.log &
nohup sudo ./mqttenv/bin/python mqttlistener.py &>/tmp/mqttlistener.log &

echo "Setup complete. Bridge and listener are running."
