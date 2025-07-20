#!/bin/bash
set -e

# Top-level setup script for the MQTT listener and broker
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install CA certificate if needed
if ! bash "$SCRIPT_DIR/install_ca.sh"; then
    echo "install_ca.sh failed or already installed, continuing..."
fi

echo "Updating package lists and installing dependencies..."
sudo apt update
sudo apt install -y git python3-venv mosquitto mosquitto-clients avahi-daemon avahi-utils build-essential python3-dev

echo "Cloning or updating the repository..."
if [ ! -d "$SCRIPT_DIR/simpsons-house" ]; then
    git clone https://github.com/roanvtkc/simpsons-house.git "$SCRIPT_DIR/simpsons-house"
fi
cd "$SCRIPT_DIR/simpsons-house"

# Create and activate Python virtual environment
if [ ! -d mqttenv ]; then
    python3 -m venv mqttenv
fi
source mqttenv/bin/activate

# Upgrade pip and install required Python packages
pip install --upgrade pip setuptools wheel
pip install paho-mqtt RPi.GPIO

# Enable and start Mosquitto broker
echo "Configuring Mosquitto listener..."
sudo tee /etc/mosquitto/conf.d/01-listener.conf >/dev/null <<EOF
listener 1883 0.0.0.0
allow_anonymous true
EOF
# Mosquitto crashes if multiple log_dest lines are present
sudo sed -i '/^log_dest file/d' /etc/mosquitto/mosquitto.conf /etc/mosquitto/conf.d/*.conf 2>/dev/null || true

sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

echo "Configuring Avahi to advertise MQTT service..."
cat <<EOF | sudo tee /etc/avahi/services/mqtt.service
<service-group>
  <name replace-wildcards="yes">Simpsons House MQTT</name>
  <service>
    <type>_mqtt._tcp</type>
    <port>1883</port>
  </service>
</service-group>
EOF
sudo systemctl restart avahi-daemon

# Launch MQTT listener in background
echo "Launching MQTT listener..."
nohup python3 mqttlistener.py &> /tmp/mqttlistener.log &

echo "Setup complete. Mosquitto broker running and mqttlistener.py started."
