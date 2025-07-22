#!/bin/bash
set -e

# Simpson's House Complete Setup Script v3.1
# Sets up MQTT + WebSocket + GPIO control for iOS app communication

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/simpsons_house_setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as pi user with sudo privileges."
        exit 1
    fi
}

# Main setup function
main() {
    log "🏠 Starting Simpson's House Complete Setup..."
    log "This will configure MQTT + WebSocket + GPIO control for iOS app"
    log "Setup log: $LOG_FILE"
    log ""
    log "📋 Note: If you're in a corporate environment with SSL inspection,"
    log "   run './install_ca.sh' first before proceeding with this setup."
    log ""
    
    # Check prerequisites
    check_root
    
    log "Updating package lists and installing dependencies..."
    sudo apt update
    sudo apt install -y git python3-venv mosquitto mosquitto-clients avahi-daemon avahi-utils build-essential python3-dev
    
    # Setup directory
    cd "$SCRIPT_DIR"
    
    log "Setting up Python virtual environment..."
    if [ ! -d mqttenv ]; then
        python3 -m venv mqttenv
    fi
    source mqttenv/bin/activate
    
    # Upgrade pip and install required Python packages
    log "Installing Python MQTT and GPIO packages..."
    pip install --upgrade pip setuptools wheel
    pip install paho-mqtt RPi.GPIO
    
    log "Configuring Mosquitto with WebSocket support..."
    # Create comprehensive Mosquitto configuration
    sudo tee /etc/mosquitto/conf.d/01-simpsons-house.conf >/dev/null <<EOF
# Simpson's House MQTT Configuration
# TCP listener for standard MQTT clients
listener 1883 0.0.0.0
protocol mqtt
allow_anonymous true

# WebSocket listener for iOS/web clients  
listener 9001 0.0.0.0
protocol websockets
allow_anonymous true

# Logging configuration
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
connection_messages true
log_timestamp true

# Performance settings
max_connections 100
max_inflight_messages 20
max_queued_messages 100
message_size_limit 1024
EOF
    
    # Remove duplicate log_dest entries to prevent crashes
    log "Cleaning up Mosquitto configuration conflicts..."
    sudo sed -i '/^log_dest file/d' /etc/mosquitto/mosquitto.conf 2>/dev/null || true
    sudo sed -i '/^log_dest file/d' /etc/mosquitto/conf.d/*.conf 2>/dev/null || true
    
    # Ensure log directory exists
    sudo mkdir -p /var/log/mosquitto
    sudo chown mosquitto:mosquitto /var/log/mosquitto
    
    # Enable and start Mosquitto
    log "Starting Mosquitto service..."
    sudo systemctl enable mosquitto
    sudo systemctl restart mosquitto
    
    # Wait and verify Mosquitto is running
    sleep 3
    if sudo systemctl is-active --quiet mosquitto; then
        log "✅ Mosquitto broker is running"
    else
        error "❌ Mosquitto failed to start"
        sudo journalctl -u mosquitto --no-pager -n 20
        exit 1
    fi
    
    # Verify ports are listening
    log "Verifying MQTT ports are listening..."
    local tcp_port=$(sudo netstat -tlnp | grep ":1883 " | wc -l)
    local ws_port=$(sudo netstat -tlnp | grep ":9001 " | wc -l)
    
    if [ "$tcp_port" -gt 0 ] && [ "$ws_port" -gt 0 ]; then
        log "✅ Both TCP (1883) and WebSocket (9001) ports are listening"
    else
        error "❌ MQTT ports not properly configured"
        sudo netstat -tlnp | grep -E "(1883|9001)"
        exit 1
    fi
    
    log "Configuring Avahi for MQTT service discovery..."
    sudo tee /etc/avahi/services/simpsons-house-mqtt.service >/dev/null <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Simpson's House MQTT Control</name>
  <service>
    <type>_mqtt._tcp</type>
    <port>1883</port>
    <txt-record>version=3.1</txt-record>
    <txt-record>device=simpsons_house</txt-record>
    <txt-record>websocket_port=9001</txt-record>
  </service>
</service-group>
EOF
    sudo systemctl restart avahi-daemon
    
    log "Setting up systemd service for Simpson's House MQTT listener..."
    # Create systemd service file
    sudo tee /etc/systemd/system/simpsons-house.service >/dev/null <<EOF
[Unit]
Description=Simpson's House MQTT Listener and GPIO Controller
After=network.target mosquitto.service
Requires=mosquitto.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/mqttenv/bin/python $SCRIPT_DIR/mqttlistener.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=PYTHONPATH=$SCRIPT_DIR
Environment=MQTT_BROKER=localhost
Environment=MQTT_PORT=1883

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable simpsons-house.service
    
    log "Starting Simpson's House MQTT listener service..."
    # Stop any existing instances
    sudo systemctl stop simpsons-house.service 2>/dev/null || true
    pkill -f mqttlistener.py 2>/dev/null || true
    sleep 2
    
    # Start the service
    sudo systemctl start simpsons-house.service
    
    # Check if service started successfully
    sleep 3
    if sudo systemctl is-active --quiet simpsons-house.service; then
        log "✅ Simpson's House MQTT listener service started successfully"
    else
        error "❌ MQTT listener service failed to start"
        sudo journalctl -u simpsons-house.service --no-pager -n 20
        exit 1
    fi
    
    # Test MQTT connectivity
    log "Testing MQTT broker connectivity..."
    if mosquitto_pub -h localhost -t test/setup -m "Simpson's House setup test" -q 0; then
        log "✅ MQTT broker test successful"
    else
        error "❌ MQTT broker test failed"
        exit 1
    fi
    
    # Display system information
    log "=== Simpson's House System Information ==="
    
    # Get IP address
    local ip_address=$(hostname -I | awk '{print $1}')
    log "🏠 Raspberry Pi IP Address: $ip_address"
    
    # Show listening ports
    log "📡 Listening ports:"
    sudo netstat -tlnp | grep -E "(1883|9001)" | while read line; do
        log "   $line"
    done
    
    # Show GPIO configuration
    log "🔧 GPIO Pin Configuration:"
    log "   💡 Light (GPIO 17) - LED + 220Ω resistor"
    log "   🌀 Fan (GPIO 27) - LED or small fan"
    log "   🚪 Door (GPIO 22) - Servo motor"
    
    # Show service status
    log "⚙️  System Services:"
    if sudo systemctl is-active --quiet mosquitto; then
        log "   ✅ Mosquitto MQTT Broker - Running"
    else
        log "   ❌ Mosquitto MQTT Broker - Stopped"
    fi
    
    if sudo systemctl is-active --quiet simpsons-house; then
        log "   ✅ Simpson's House Listener - Running"
    else
        log "   ❌ Simpson's House Listener - Stopped"
    fi
    
    if sudo systemctl is-active --quiet avahi-daemon; then
        log "   ✅ Avahi mDNS Service - Running"
    else
        log "   ❌ Avahi mDNS Service - Stopped"
    fi
    
    log ""
    log "=== iOS App Configuration ==="
    log "📱 Use these settings in your Swift Playgrounds app:"
    log "   🌐 Host: $ip_address"
    log "   🔌 WebSocket Port: 9001"
    log "   📨 MQTT Topics: home/light, home/fan, home/door"
    log ""
    log "🎮 Device Controls:"
    log "   💡 Light: Send 'ON' or 'OFF' to home/light"
    log "   🌀 Fan: Send 'ON' or 'OFF' to home/fan"
    log "   🚪 Door: Send 'ON' or 'OFF' to home/door"
    log ""
    log "🔧 System Management Commands:"
    log "   📊 Status: sudo systemctl status simpsons-house"
    log "   📋 Logs:   sudo journalctl -u simpsons-house -f"
    log "   🔄 Restart: sudo systemctl restart simpsons-house"
    log "   🛠️  MQTT Test: mosquitto_pub -h localhost -t home/light -m ON"
    log ""
    log "📁 Log Files:"
    log "   🏠 Setup: $LOG_FILE"
    log "   📡 MQTT Listener: sudo journalctl -u simpsons-house -f"
    log "   🦟 Mosquitto: /var/log/mosquitto/mosquitto.log"
    log ""
    log "🔒 Corporate Networks:"
    log "   If you encounter SSL certificate errors, run: ./install_ca.sh"
    log ""
    log "🎉 Simpson's House is now ready for iOS control!"
    log "Connect your iPhone/iPad and start controlling the house! 🏠✨"
}

# Run main function
main "$@"
