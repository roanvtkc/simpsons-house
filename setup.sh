#!/bin/bash
set -e

# Simpson's House Complete Setup Script v3.2 with ULN2003 Motor Driver
# Sets up MQTT + WebSocket + GPIO control for iOS app communication
# Now includes ULN2003 motor driver for professional stepper motor control

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/simpsons_house_setup.log"
DEBUG_LOG="/tmp/simpsons_house_debug.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging functions
log() {
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[${timestamp}]${NC} $1" | tee -a "$LOG_FILE"
    echo "[${timestamp}] INFO: $1" >> "$DEBUG_LOG"
}

warn() {
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[${timestamp}] WARNING:${NC} $1" | tee -a "$LOG_FILE"
    echo "[${timestamp}] WARN: $1" >> "$DEBUG_LOG"
}

error() {
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[${timestamp}] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    echo "[${timestamp}] ERROR: $1" >> "$DEBUG_LOG"
}

debug() {
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${CYAN}[${timestamp}] DEBUG:${NC} $1"
    echo "[${timestamp}] DEBUG: $1" >> "$DEBUG_LOG"
}

step() {
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${PURPLE}[${timestamp}] STEP:${NC} $1" | tee -a "$LOG_FILE"
    echo "[${timestamp}] STEP: $1" >> "$DEBUG_LOG"
}

# Enhanced command execution with logging
run_cmd() {
    local cmd="$1"
    local description="$2"
    
    debug "Executing: $cmd"
    step "$description"
    
    if eval "$cmd" >> "$DEBUG_LOG" 2>&1; then
        log "✅ $description - SUCCESS"
        return 0
    else
        local exit_code=$?
        error "❌ $description - FAILED (exit code: $exit_code)"
        error "Command: $cmd"
        error "Check debug log: $DEBUG_LOG"
        return $exit_code
    fi
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as pi user with sudo privileges."
        exit 1
    fi
    log "✅ Running as non-root user: $(whoami)"
}

# Sync time with corporate domain controllers
sync_corporate_time() {
    step "Synchronizing time with corporate domain controllers..."
    
    # Install ntpdate if not available (this worked for you)
    debug "Installing ntpdate for time synchronization..."
    if ! command -v ntpdate >/dev/null 2>&1; then
        log "Installing ntpdate..."
        if sudo apt install -y ntpdate --fix-missing >> "$DEBUG_LOG" 2>&1; then
            log "✅ ntpdate installed successfully"
        else
            warn "⚠️ Could not install ntpdate, trying manual time sync"
        fi
    else
        log "✅ ntpdate already available"
    fi
    
    # Sync with domain controllers
    log "🕐 Attempting time sync with Domain Controllers..."
    local time_synced=false
    
    for dc in 10.20.1.30 10.20.1.31; do
        debug "Trying DC: $dc"
        if ping -c 1 -W 3 $dc >/dev/null 2>&1; then
            debug "DC $dc is reachable"
            if timeout 10 sudo ntpdate -s $dc >> "$DEBUG_LOG" 2>&1; then
                log "✅ Successfully synced time with DC $dc"
                time_synced=true
                break
            else
                debug "❌ Time sync failed with DC $dc"
            fi
        else
            debug "❌ DC $dc is not reachable"
        fi
    done
    
    if [ "$time_synced" = false ]; then
        warn "⚠️ Could not sync with domain controllers"
        warn "You may need to set time manually: sudo timedatectl set-time 'YYYY-MM-DD HH:MM:SS'"
    fi
    
    local current_time=$(date)
    log "Current system time: $current_time"
    
    # Check if time looks reasonable (year should be 2025)
    local year=$(date +%Y)
    if [ "$year" -eq 2025 ]; then
        log "✅ System time appears correct"
    else
        warn "⚠️ System time may still be incorrect (year: $year)"
        warn "Package repositories may reject updates with incorrect time"
    fi
}

# Check system requirements
check_system() {
    step "Checking system requirements..."
    
    # Check OS
    local os_info=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
    log "Operating System: $os_info"
    
    # Check architecture
    local arch=$(uname -m)
    log "Architecture: $arch"
    
    # Check Python version
    local python_version=$(python3 --version 2>/dev/null || echo "Python3 not found")
    log "Python: $python_version"
    
    # Check available space
    local disk_space=$(df -h . | tail -1 | awk '{print $4}')
    log "Available disk space: $disk_space"
    
    # Check memory
    local memory=$(free -h | grep Mem | awk '{print $2}')
    log "Total memory: $memory"
    
    # Check network connectivity
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log "✅ Internet connectivity: Available"
    else
        warn "❌ Internet connectivity: Limited or unavailable"
        log "Note: Will attempt to use corporate network resources"
    fi
}

# Install system packages with detailed logging
install_packages() {
    step "Installing system packages..."
    
    local packages="git python3-venv mosquitto mosquitto-clients avahi-daemon avahi-utils build-essential python3-dev"
    log "Packages to install: $packages"
    
    # Update package lists with time-sensitive retry
    log "Updating package lists (this may take time in corporate environments)..."
    local update_attempts=0
    local max_attempts=3
    
    while [ $update_attempts -lt $max_attempts ]; do
        update_attempts=$((update_attempts + 1))
        debug "Package update attempt $update_attempts of $max_attempts"
        
        if sudo apt update >> "$DEBUG_LOG" 2>&1; then
            log "✅ Package lists updated successfully"
            break
        else
            if [ $update_attempts -eq $max_attempts ]; then
                error "❌ Failed to update package lists after $max_attempts attempts"
                error "This is often caused by:"
                error "  - Incorrect system time (check: date)"
                error "  - Corporate firewall blocking repositories"
                error "  - Network connectivity issues"
                debug "Checking current time: $(date)"
                return 1
            else
                warn "⚠️ Package update attempt $update_attempts failed, retrying..."
                sleep 5
            fi
        fi
    done
    
    # Install packages one by one for better error tracking
    for package in $packages; do
        debug "Checking if $package is already installed..."
        if dpkg -l | grep -q "^ii  $package "; then
            log "✅ $package - already installed"
        else
            debug "Installing package: $package"
            if sudo apt install -y $package >> "$DEBUG_LOG" 2>&1; then
                log "✅ $package - installed successfully"
            else
                warn "⚠️ $package - installation failed, continuing anyway"
                debug "Failed package: $package"
            fi
        fi
    done
    
    # Verify critical installations
    step "Verifying critical package installations..."
    local critical_packages="git python3-venv mosquitto"
    local missing_critical=""
    
    for package in $critical_packages; do
        if dpkg -l | grep -q "^ii  $package "; then
            log "✅ $package - verified installed"
        else
            error "❌ $package - CRITICAL PACKAGE MISSING"
            missing_critical="$missing_critical $package"
        fi
    done
    
    if [ -n "$missing_critical" ]; then
        error "❌ Critical packages missing:$missing_critical"
        error "Setup cannot continue without these packages"
        error "Please contact IT support or install manually"
        return 1
    fi
}

# Setup Python environment with detailed logging
setup_python_env() {
    step "Setting up Python virtual environment..."
    
    cd "$SCRIPT_DIR"
    debug "Working directory: $(pwd)"
    
    if [ -d "mqttenv" ]; then
        log "Virtual environment already exists"
        run_cmd "rm -rf mqttenv" "Removing existing virtual environment"
    fi
    
    run_cmd "python3 -m venv mqttenv" "Creating Python virtual environment"
    
    debug "Activating virtual environment..."
    source mqttenv/bin/activate
    log "✅ Virtual environment activated"
    
    # Check Python version in venv
    local venv_python_version=$(python --version)
    log "Virtual environment Python: $venv_python_version"
    
    run_cmd "pip install --upgrade pip setuptools wheel" "Upgrading pip and setuptools"
    run_cmd "pip install paho-mqtt RPi.GPIO" "Installing Python packages"
    
    # Verify Python packages
    step "Verifying Python package installations..."
    python -c "import paho.mqtt.client as mqtt; print('paho-mqtt imported successfully')" >> "$DEBUG_LOG" 2>&1 && log "✅ paho-mqtt - verified" || error "❌ paho-mqtt - import failed"
    python -c "import RPi.GPIO as GPIO; print('RPi.GPIO imported successfully')" >> "$DEBUG_LOG" 2>&1 && log "✅ RPi.GPIO - verified" || error "❌ RPi.GPIO - import failed"
}

# Configure Mosquitto with detailed logging
configure_mosquitto() {
    step "Configuring Mosquitto MQTT broker..."
    
    debug "Creating Mosquitto configuration directory..."
    sudo mkdir -p /etc/mosquitto/conf.d
    
    debug "Writing Mosquitto configuration..."
    sudo tee /etc/mosquitto/conf.d/01-simpsons-house.conf >/dev/null <<EOF
# Simpson's House MQTT Configuration with ULN2003 Motor Driver
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
    log "✅ Mosquitto configuration written"
    
    # Clean up duplicate log entries
    run_cmd "sudo sed -i '/^log_dest file/d' /etc/mosquitto/mosquitto.conf 2>/dev/null || true" "Cleaning duplicate log entries"
    
    # Create log directory
    run_cmd "sudo mkdir -p /var/log/mosquitto" "Creating Mosquitto log directory"
    run_cmd "sudo chown mosquitto:mosquitto /var/log/mosquitto" "Setting Mosquitto log permissions"
    
    # Enable and start Mosquitto
    run_cmd "sudo systemctl enable mosquitto" "Enabling Mosquitto service"
    run_cmd "sudo systemctl restart mosquitto" "Starting Mosquitto service"
    
    # Wait for service to start
    debug "Waiting for Mosquitto to start..."
    sleep 3
    
    # Verify Mosquitto is running
    if sudo systemctl is-active --quiet mosquitto; then
        log "✅ Mosquitto service is running"
    else
        error "❌ Mosquitto service failed to start"
        debug "Mosquitto service status:"
        sudo systemctl status mosquitto >> "$DEBUG_LOG" 2>&1
        debug "Mosquitto journal logs:"
        sudo journalctl -u mosquitto --no-pager -n 20 >> "$DEBUG_LOG" 2>&1
        return 1
    fi
    
    # Verify ports are listening
    step "Verifying MQTT ports..."
    local tcp_port=$(sudo netstat -tlnp | grep ":1883 " | wc -l)
    local ws_port=$(sudo netstat -tlnp | grep ":9001 " | wc -l)
    
    debug "TCP port 1883 listeners: $tcp_port"
    debug "WebSocket port 9001 listeners: $ws_port"
    
    if [ "$tcp_port" -gt 0 ] && [ "$ws_port" -gt 0 ]; then
        log "✅ Both TCP (1883) and WebSocket (9001) ports are listening"
        sudo netstat -tlnp | grep -E "(1883|9001)" >> "$DEBUG_LOG"
    else
        error "❌ MQTT ports not properly configured"
        sudo netstat -tlnp | grep -E "(1883|9001)" | tee -a "$DEBUG_LOG"
        return 1
    fi
}

# Configure Avahi service discovery
configure_avahi() {
    step "Configuring Avahi mDNS service discovery..."
    
    sudo tee /etc/avahi/services/simpsons-house-mqtt.service >/dev/null <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Simpson's House MQTT Control with ULN2003</name>
  <service>
    <type>_mqtt._tcp</type>
    <port>1883</port>
    <txt-record>version=3.2</txt-record>
    <txt-record>device=simpsons_house</txt-record>
    <txt-record>motor_driver=ULN2003</txt-record>
    <txt-record>websocket_port=9001</txt-record>
  </service>
</service-group>
EOF
    log "✅ Avahi service configuration written"
    
    run_cmd "sudo systemctl restart avahi-daemon" "Restarting Avahi daemon"
    
    # Verify Avahi is running
    if sudo systemctl is-active --quiet avahi-daemon; then
        log "✅ Avahi daemon is running"
    else
        warn "❌ Avahi daemon not running properly"
    fi
}

# Setup systemd service
setup_systemd_service() {
    step "Setting up systemd service for Simpson's House..."
    
    debug "Creating systemd service file..."
    sudo tee /etc/systemd/system/simpsons-house.service >/dev/null <<EOF
[Unit]
Description=Simpson's House MQTT Listener and GPIO Controller with ULN2003 Motor Driver
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
    log "✅ Systemd service file created"
    
    # Reload systemd
    run_cmd "sudo systemctl daemon-reload" "Reloading systemd daemon"
    run_cmd "sudo systemctl enable simpsons-house.service" "Enabling Simpson's House service"
    
    # Stop any existing instances
    debug "Stopping any existing instances..."
    sudo systemctl stop simpsons-house.service 2>/dev/null || true
    pkill -f mqttlistener.py 2>/dev/null || true
    sleep 2
    
    # Check if mqttlistener.py exists
    if [ ! -f "$SCRIPT_DIR/mqttlistener.py" ]; then
        error "❌ mqttlistener.py not found in $SCRIPT_DIR"
        error "Please ensure mqttlistener.py is in the project directory"
        return 1
    fi
    log "✅ mqttlistener.py found at $SCRIPT_DIR/mqttlistener.py"
    
    # Start the service
    run_cmd "sudo systemctl start simpsons-house.service" "Starting Simpson's House service"
    
    # Wait for service to start
    debug "Waiting for service to start..."
    sleep 3
    
    # Check service status
    if sudo systemctl is-active --quiet simpsons-house.service; then
        log "✅ Simpson's House service is running"
    else
        error "❌ Simpson's House service failed to start"
        debug "Service status:"
        sudo systemctl status simpsons-house.service >> "$DEBUG_LOG" 2>&1
        debug "Service journal logs:"
        sudo journalctl -u simpsons-house.service --no-pager -n 20 >> "$DEBUG_LOG" 2>&1
        return 1
    fi
}

# Test MQTT functionality
test_mqtt() {
    step "Testing MQTT broker functionality..."
    
    debug "Testing MQTT publish..."
    if mosquitto_pub -h localhost -t test/setup -m "Simpson's House ULN2003 setup test $(date)" -q 0; then
        log "✅ MQTT publish test successful"
    else
        error "❌ MQTT publish test failed"
        return 1
    fi
    
    debug "Testing MQTT subscribe (background test)..."
    timeout 5 mosquitto_sub -h localhost -t test/setup -C 1 >> "$DEBUG_LOG" 2>&1 &
    sleep 1
    mosquitto_pub -h localhost -t test/setup -m "Subscribe test message" -q 0
    wait
    log "✅ MQTT subscribe test completed"
}

# Display comprehensive system information
display_system_info() {
    log ""
    log "=== Simpson's House System Information with ULN2003 ==="
    
    # Get IP address
    local ip_address=$(hostname -I | awk '{print $1}')
    log "🏠 Raspberry Pi IP Address: $ip_address"
    log "🖥️  Hostname: $(hostname)"
    
    # Show listening ports
    log "📡 Listening ports:"
    sudo netstat -tlnp | grep -E "(1883|9001)" | while read line; do
        log "   $line"
    done
    
    # Show GPIO configuration for ULN2003 setup
    log "🔧 ULN2003 GPIO Pin Configuration (BCM numbering):"
    log "   💡 Light (GPIO 17) - Pin 11 - LED + 220Ω resistor"
    log "   🌀 ULN2003 Stepper Driver:"
    log "      - IN1 (GPIO 27) - Pin 13"
    log "      - IN2 (GPIO 18) - Pin 12"
    log "      - IN3 (GPIO 22) - Pin 15"
    log "      - IN4 (GPIO 24) - Pin 18"
    log "   🚪 Door Servo (GPIO 23) - Pin 16 - Servo motor"
    
    # Show ULN2003 wiring information
    log ""
    log "🔌 ULN2003 Wiring Requirements:"
    log "   ⚡ Power: ULN2003 VCC → Pi 5V (Pin 4)"
    log "   🔗 Ground: ULN2003 GND → Pi GND"
    log "   🎛️  Control: Pi GPIO pins → ULN2003 IN1-IN4"
    log "   🔧 Motor: Stepper motor connector → ULN2003 board"
    
    # Show service status
    log ""
    log "⚙️  System Services:"
    if sudo systemctl is-active --quiet mosquitto; then
        log "   ✅ Mosquitto MQTT Broker - Running"
    else
        log "   ❌ Mosquitto MQTT Broker - Stopped"
    fi
    
    if sudo systemctl is-active --quiet simpsons-house; then
        log "   ✅ Simpson's House ULN2003 Controller - Running"
    else
        log "   ❌ Simpson's House ULN2003 Controller - Stopped"
    fi
    
    if sudo systemctl is-active --quiet avahi-daemon; then
        log "   ✅ Avahi mDNS Service - Running"
    else
        log "   ❌ Avahi mDNS Service - Stopped"
    fi
    
    # Show process information
    log "🔄 Process Information:"
    local mosquitto_pid=$(pgrep mosquitto || echo "Not running")
    local python_pid=$(pgrep -f mqttlistener.py || echo "Not running")
    log "   Mosquitto PID: $mosquitto_pid"
    log "   MQTT Listener PID: $python_pid"
    
    log ""
    log "=== iOS App Configuration ==="
    log "📱 Use these settings in your Swift Playgrounds app:"
    log "   🌐 Host: $ip_address"
    log "   🔌 WebSocket Port: 9001"
    log "   📨 MQTT Topics: home/light, home/garage, home/door"
    log ""
    log "🎮 Device Controls with ULN2003:"
    log "   💡 Light: Send 'ON' or 'OFF' to home/light"
    log "   🚗 Garage Door: Send 'OPEN' or 'CLOSE' to home/garage"
    log "   🚪 Door: Send 'ON' (open) or 'OFF' (close) to home/door"
    log ""
    log "🔧 Hardware Testing:"
    log "   🧪 Test ULN2003: python3 ULN2003_test.py"
    log "   🧪 Test All GPIO: python3 gpio_test.py"
    log ""
    log "🔧 System Management Commands:"
    log "   📊 Status: sudo systemctl status simpsons-house"
    log "   📋 Logs:   sudo journalctl -u simpsons-house -f"
    log "   🔄 Restart: sudo systemctl restart simpsons-house"
    log "   🛠️  MQTT Test: mosquitto_pub -h localhost -t home/garage -m OPEN"
    log ""
    log "📁 Log Files:"
    log "   🏠 Setup: $LOG_FILE"
    log "   🔍 Debug: $DEBUG_LOG"
    log "   📡 MQTT Listener: sudo journalctl -u simpsons-house -f"
    log "   🦟 Mosquitto: /var/log/mosquitto/mosquitto.log"
    log ""
    log "⚠️  ULN2003 Safety Notes:"
    log "   🔋 Always use external power supply for motor (9V battery)"
    log "   🔗 Ensure all grounds are connected together"
    log "   🌡️  ULN2003 IC may get warm during operation"
    log "   🔧 Test motor direction before final assembly"
    log ""
    log "🔒 Corporate Networks:"
    log "   If you encounter SSL certificate errors, run: ./install_ca.sh"
    log ""
}

# Main setup function
main() {
    # Initialize logging
    echo "Simpson's House Setup with ULN2003 - $(date)" > "$LOG_FILE"
    echo "Simpson's House Debug Log with ULN2003 - $(date)" > "$DEBUG_LOG"
    
    log "🏠 Starting Simpson's House Complete Setup v3.2 with ULN2003 Motor Driver..."
    log "This will configure MQTT + WebSocket + GPIO control + ULN2003 for iOS app"
    log "Setup log: $LOG_FILE"
    log "Debug log: $DEBUG_LOG"
    log ""
    log "🔧 NEW: Now includes ULN2003 motor driver for professional stepper motor control!"
    log "📋 Note: If you're in a corporate environment with SSL inspection,"
    log "   run './install_ca.sh' first before proceeding with this setup."
    log ""
    log "⚠️  Hardware Requirements:"
    log "   • ULN2003 Motor Driver IC (16-pin DIP)"
    log "   • stepper motor (3-6V, ≤600mA)"
    log "   • External 9V battery for motor power"
    log "   • Updated GPIO wiring per README.md"
    log ""
    
    # Run setup steps
    check_root
    sync_corporate_time
    check_system
    install_packages
    setup_python_env
    configure_mosquitto
    configure_avahi
    setup_systemd_service
    test_mqtt
    display_system_info
    
    log "🎉 Simpson's House with ULN2003 setup completed successfully!"
    log "🌀 Your stepper motor is now ready for professional control!"
    log "Connect your iPhone/iPad and start controlling the house! 🏠✨"
    log ""
    log "📋 Next Steps:"
    log "   1. Test your ULN2003 wiring: python3 ULN2003_test.py"
    log "   2. Test all GPIO pins: python3 gpio_test.py"
    log "   3. Connect your iOS app and enjoy motor control!"
    log ""
    log "📋 If you encounter any issues:"
    log "   1. Check the debug log: $DEBUG_LOG"
    log "   2. Check service logs: sudo journalctl -u simpsons-house -f"
    log "   3. Verify ULN2003 hardware connections match the GPIO configuration"
    log "   4. Ensure 9V battery is connected and charged"
}

# Error handling
trap 'error "Setup failed at line $LINENO. Check debug log: $DEBUG_LOG"' ERR

# Run main function
main "$@"
