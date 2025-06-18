#!/bin/bash
set -e

# Top-level setup script for the MQTT bridge & listener
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Run the CA-install helper in its own process and guard errors
if ! bash "$SCRIPT_DIR/install_ca.sh"; then
    echo "install_ca.sh failed, continuing with main setup..."
fi

echo "Installing required packages..."
sudo apt update
sudo apt install -y git python3-venv mosquitto build-essential python3-dev

# Clone the repo if needed
if [ ! -f mqttbridge.py ]; then
    git clone https://github.com/roanvtkc/simpsons-house.git
    cd simpsons-house
fi

# Create Python virtual environment
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
