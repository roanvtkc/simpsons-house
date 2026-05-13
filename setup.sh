#!/bin/bash
set -e

# Simpson's House Complete Setup Script v3.3
# Sets up MQTT + WebSocket + GPIO control for iOS app communication

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
NC='\033[0m'

# Logging functions
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

# Run a command with logging — uses python -m pip style paths to avoid
# bare-command PATH issues inside eval after venv activation
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

# -----------------------------------------------------------------------------
# Check root
# -----------------------------------------------------------------------------

check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "Run as the pi user, not root. The script uses sudo internally."
        exit 1
    fi
    log "✅ Running as non-root user: $(whoami)"
}

# -----------------------------------------------------------------------------
# Time sync
# -----------------------------------------------------------------------------
# ntpdate was removed from Debian trixie. We use systemd-timesyncd with
# reliable public NTP servers, then fall back to reading the Date: header
# from the internal cert server (same approach as install_ca.sh).

sync_system_time() {
    step "Synchronising system clock..."
    log "Current Pi time: $(date)"

    # Configure reliable NTP servers
    sudo bash -c 'cat > /etc/systemd/timesyncd.conf << EOF
[Time]
NTP=pool.ntp.org time.cloudflare.com
FallbackNTP=time.google.com
EOF'
    sudo systemctl restart systemd-timesyncd
    sleep 5

    if timedatectl status | grep -q "System clock synchronized: yes"; then
        log "✅ System clock synchronised via NTP: $(date)"
        return 0
    fi

    warn "NTP sync not confirmed (NTP may be blocked on this network)"
    warn "Trying HTTP date header fallback from internal server..."

    local http_date
    http_date=$(curl -sI --max-time 5 "http://10.20.1.83:8081/" 2>/dev/null \
                | grep -i "^Date:" | sed 's/[Dd]ate: //' | tr -d '\r\n')

    if [ -n "$http_date" ]; then
        sudo date -s "$http_date" >/dev/null 2>&1
        log "✅ Clock set via HTTP header: $(date)"
    else
        warn "Could not sync clock automatically — continuing anyway"
        warn "If package installs fail with date errors, run: sudo date -s 'YYYY-MM-DD HH:MM:SS'"
    fi

    # Sanity-check: year should be somewhere reasonable
    local year
    year=$(date +%Y)
    if [ "$year" -lt 2024 ] || [ "$year" -gt 2030 ]; then
        warn "Year $year looks wrong — package repos may reject updates"
    else
        log "✅ System time appears correct ($(date))"
    fi
}

# -----------------------------------------------------------------------------
# System requirements
# -----------------------------------------------------------------------------

check_system() {
    step "Checking system requirements..."

    log "Operating System: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
    log "Architecture: $(uname -m)"
    log "Python: $(python3 --version 2>/dev/null || echo 'Python3 not found')"
    log "Available disk space: $(df -h . | tail -1 | awk '{print $4}')"
    log "Total memory: $(free -h | grep Mem | awk '{print $2}')"

    # Check internet via HTTPS to a real host — 8.8.8.8 is blocked by FortiGate
    if curl -sf --max-time 10 https://deb.debian.org > /dev/null 2>&1; then
        log "✅ Internet connectivity: Available"
    else
        warn "Internet connectivity limited — will attempt using apt mirrors directly"
    fi
}

# -----------------------------------------------------------------------------
# System packages
# -----------------------------------------------------------------------------

install_packages() {
    step "Installing system packages..."

    local packages="git python3-venv mosquitto mosquitto-clients avahi-daemon avahi-utils build-essential python3-dev"
    log "Packages to install: $packages"

    log "Updating package lists..."
    local attempt=0
    local max=3
    while [ $attempt -lt $max ]; do
        attempt=$((attempt + 1))
        debug "apt update attempt $attempt of $max"
        if sudo apt update >> "$DEBUG_LOG" 2>&1; then
            log "✅ Package lists updated"
            break
        else
            if [ $attempt -eq $max ]; then
                error "Failed to update package lists after $max attempts"
                error "Check: system time ($(date)), network, FortiGate cert installed?"
                return 1
            fi
            warn "apt update attempt $attempt failed, retrying in 5s..."
            sleep 5
        fi
    done

    for package in $packages; do
        if dpkg -l | grep -q "^ii  $package "; then
            log "✅ $package - already installed"
        else
            debug "Installing: $package"
            if sudo apt install -y "$package" >> "$DEBUG_LOG" 2>&1; then
                log "✅ $package - installed"
            else
                warn "⚠️ $package - installation failed, continuing"
            fi
        fi
    done

    # Verify critical packages
    step "Verifying critical packages..."
    local missing=""
    for package in git python3-venv mosquitto; do
        if dpkg -l | grep -q "^ii  $package "; then
            log "✅ $package - verified"
        else
            error "❌ $package - MISSING"
            missing="$missing $package"
        fi
    done

    if [ -n "$missing" ]; then
        error "Critical packages missing:$missing — cannot continue"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Python virtual environment
# -----------------------------------------------------------------------------
# Uses `python -m pip` throughout — bare `pip` is unreliable after venv
# activation inside eval because PATH expansion can vary by shell/version.

setup_python_env() {
    step "Setting up Python virtual environment..."

    cd "$SCRIPT_DIR"
    debug "Working directory: $(pwd)"

    if [ -d "mqttenv" ]; then
        log "Removing existing virtual environment..."
        rm -rf mqttenv
    fi

    run_cmd "python3 -m venv mqttenv" "Creating Python virtual environment"

    # Activate and capture the venv python path explicitly
    source mqttenv/bin/activate
    local VENV_PYTHON="$SCRIPT_DIR/mqttenv/bin/python"
    local VENV_PIP="$SCRIPT_DIR/mqttenv/bin/python -m pip"
    log "✅ Virtual environment activated — Python: $($VENV_PYTHON --version)"

    # Upgrade pip using python -m pip (avoids bare 'pip' PATH issues)
    run_cmd "$VENV_PYTHON -m pip install --upgrade pip setuptools wheel" \
            "Upgrading pip and setuptools"

    # Install paho-mqtt (required)
    run_cmd "$VENV_PYTHON -m pip install paho-mqtt" "Installing paho-mqtt"

    # Install GPIO library — RPi.GPIO for Python ≤3.12, lgpio for 3.13+
    local python_minor
    python_minor=$($VENV_PYTHON -c "import sys; print(sys.version_info.minor)")
    local python_major
    python_major=$($VENV_PYTHON -c "import sys; print(sys.version_info.major)")

    log "Python version in venv: $python_major.$python_minor"

    if [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 13 ]; then
        warn "Python 3.13+ detected — RPi.GPIO is not supported on this version"
        log "Installing lgpio as GPIO library..."
        if $VENV_PYTHON -m pip install lgpio >> "$DEBUG_LOG" 2>&1; then
            log "✅ lgpio installed"
            # Also try rpi-lgpio which provides an RPi.GPIO-compatible API
            if $VENV_PYTHON -m pip install rpi-lgpio >> "$DEBUG_LOG" 2>&1; then
                log "✅ rpi-lgpio installed (RPi.GPIO-compatible wrapper)"
            else
                warn "rpi-lgpio not available — mqttlistener.py may need updating for lgpio API"
            fi
        else
            warn "lgpio install failed — trying RPi.GPIO anyway (may not work)"
            $VENV_PYTHON -m pip install RPi.GPIO >> "$DEBUG_LOG" 2>&1 || \
                warn "RPi.GPIO also failed — GPIO control will not work until a compatible library is installed"
        fi
    else
        run_cmd "$VENV_PYTHON -m pip install RPi.GPIO" "Installing RPi.GPIO"
    fi

    # Verify imports
    step "Verifying Python package installations..."
    if $VENV_PYTHON -c "import paho.mqtt.client" >> "$DEBUG_LOG" 2>&1; then
        log "✅ paho-mqtt import OK"
    else
        error "❌ paho-mqtt import failed"
    fi

    # Try RPi.GPIO first, then lgpio, then rpi-lgpio
    if $VENV_PYTHON -c "import RPi.GPIO" >> "$DEBUG_LOG" 2>&1; then
        log "✅ RPi.GPIO import OK"
    elif $VENV_PYTHON -c "import lgpio" >> "$DEBUG_LOG" 2>&1; then
        log "✅ lgpio import OK (RPi.GPIO replacement)"
    else
        warn "No GPIO library imported successfully — hardware control will fail"
        warn "Run: $VENV_PYTHON -m pip install rpi-lgpio"
    fi
}

# -----------------------------------------------------------------------------
# Mosquitto
# -----------------------------------------------------------------------------

configure_mosquitto() {
    step "Configuring Mosquitto MQTT broker..."

    sudo mkdir -p /etc/mosquitto/conf.d

    sudo tee /etc/mosquitto/conf.d/01-simpsons-house.conf >/dev/null <<EOF
# Simpson's House MQTT Configuration
# TCP for standard MQTT clients
listener 1883 0.0.0.0
protocol mqtt
allow_anonymous true

# WebSocket for iOS app
listener 9001 0.0.0.0
protocol websockets
allow_anonymous true

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
connection_messages true
log_timestamp true

# Performance
max_connections 100
max_inflight_messages 20
max_queued_messages 100
message_size_limit 1024
EOF
    log "✅ Mosquitto configuration written"

    # Remove duplicate log_dest lines from main config if present
    sudo sed -i '/^log_dest file/d' /etc/mosquitto/mosquitto.conf 2>/dev/null || true

    run_cmd "sudo mkdir -p /var/log/mosquitto" "Creating Mosquitto log directory"
    run_cmd "sudo chown mosquitto:mosquitto /var/log/mosquitto" "Setting Mosquitto log permissions"
    run_cmd "sudo systemctl enable mosquitto" "Enabling Mosquitto service"
    run_cmd "sudo systemctl restart mosquitto" "Starting Mosquitto service"

    sleep 3

    if sudo systemctl is-active --quiet mosquitto; then
        log "✅ Mosquitto service is running"
    else
        error "❌ Mosquitto service failed to start"
        sudo journalctl -u mosquitto --no-pager -n 20 >> "$DEBUG_LOG" 2>&1
        return 1
    fi

    # Verify ports — use ss (replaces deprecated netstat)
    step "Verifying MQTT ports..."
    local tcp_port ws_port
    tcp_port=$(ss -tlnp | grep -c ":1883 " || true)
    ws_port=$(ss -tlnp  | grep -c ":9001 " || true)

    debug "TCP 1883 listeners: $tcp_port  |  WS 9001 listeners: $ws_port"

    if [ "$tcp_port" -gt 0 ] && [ "$ws_port" -gt 0 ]; then
        log "✅ TCP (1883) and WebSocket (9001) ports are listening"
    else
        error "❌ Expected ports not open — check Mosquitto config"
        ss -tlnp | grep -E "(1883|9001)" | tee -a "$DEBUG_LOG" || true
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Avahi mDNS
# -----------------------------------------------------------------------------

configure_avahi() {
    step "Configuring Avahi mDNS service discovery..."

    sudo tee /etc/avahi/services/simpsons-house-mqtt.service >/dev/null <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Simpson's House MQTT Control</name>
  <service>
    <type>_mqtt._tcp</type>
    <port>1883</port>
    <txt-record>version=3.3</txt-record>
    <txt-record>device=simpsons_house</txt-record>
    <txt-record>websocket_port=9001</txt-record>
  </service>
</service-group>
EOF
    log "✅ Avahi service configuration written"

    run_cmd "sudo systemctl restart avahi-daemon" "Restarting Avahi daemon"

    if sudo systemctl is-active --quiet avahi-daemon; then
        log "✅ Avahi daemon is running"
    else
        warn "Avahi daemon not running — mDNS discovery unavailable"
    fi
}

# -----------------------------------------------------------------------------
# systemd service
# -----------------------------------------------------------------------------

setup_systemd_service() {
    step "Setting up systemd service for Simpson's House..."

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
Environment=PYTHONPATH=$SCRIPT_DIR
Environment=MQTT_BROKER=localhost
Environment=MQTT_PORT=1883

[Install]
WantedBy=multi-user.target
EOF
    log "✅ systemd service file created"

    run_cmd "sudo systemctl daemon-reload" "Reloading systemd"
    run_cmd "sudo systemctl enable simpsons-house.service" "Enabling service"

    sudo systemctl stop simpsons-house.service 2>/dev/null || true
    pkill -f mqttlistener.py 2>/dev/null || true
    sleep 2

    if [ ! -f "$SCRIPT_DIR/mqttlistener.py" ]; then
        error "mqttlistener.py not found in $SCRIPT_DIR"
        return 1
    fi
    log "✅ mqttlistener.py found"

    run_cmd "sudo systemctl start simpsons-house.service" "Starting service"
    sleep 3

    if sudo systemctl is-active --quiet simpsons-house.service; then
        log "✅ Simpson's House service is running"
    else
        error "❌ Service failed to start"
        sudo journalctl -u simpsons-house.service --no-pager -n 30 | tee -a "$DEBUG_LOG"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# MQTT smoke test
# -----------------------------------------------------------------------------

test_mqtt() {
    step "Testing MQTT broker..."

    if mosquitto_pub -h localhost -t test/setup -m "Simpson's House setup test $(date)" -q 0; then
        log "✅ MQTT publish test successful"
    else
        error "❌ MQTT publish test failed"
        return 1
    fi

    timeout 5 mosquitto_sub -h localhost -t test/setup -C 1 >> "$DEBUG_LOG" 2>&1 &
    sleep 1
    mosquitto_pub -h localhost -t test/setup -m "Subscribe test" -q 0
    wait
    log "✅ MQTT subscribe test completed"
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

display_summary() {
    local ip_address
    ip_address=$(hostname -I | awk '{print $1}')

    log ""
    log "=== Simpson's House Setup Complete ==="
    log ""
    log "🏠 Pi IP Address : $ip_address"
    log "🖥️  Hostname      : $(hostname)"
    log ""
    log "⚙️  Services:"
    sudo systemctl is-active --quiet mosquitto      && log "   ✅ Mosquitto MQTT Broker"        || log "   ❌ Mosquitto MQTT Broker"
    sudo systemctl is-active --quiet simpsons-house && log "   ✅ Simpson's House Controller"   || log "   ❌ Simpson's House Controller"
    sudo systemctl is-active --quiet avahi-daemon   && log "   ✅ Avahi mDNS"                   || log "   ❌ Avahi mDNS"
    log ""
    log "📡 MQTT Ports (ss -tlnp):"
    ss -tlnp | grep -E "(1883|9001)" | while read -r line; do log "   $line"; done
    log ""
    log "🔧 GPIO Pin Configuration (BCM):"
    log "   💡 Light        GPIO 17  (Pin 11) — LED + 220Ω"
    log "   🚗 Garage IN1   GPIO 27  (Pin 13)"
    log "   🚗 Garage IN2   GPIO 18  (Pin 12)"
    log "   🚗 Garage IN3   GPIO 22  (Pin 15)"
    log "   🚗 Garage IN4   GPIO 24  (Pin 18)"
    log "   🚪 Door Servo   GPIO 23  (Pin 16)"
    log ""
    log "📱 iOS App Settings:"
    log "   Host: $ip_address"
    log "   WebSocket Port: 9001"
    log "   Topics: home/light  home/garage  home/door"
    log ""
    log "🔧 Useful Commands:"
    log "   sudo systemctl status simpsons-house"
    log "   sudo journalctl -u simpsons-house -f"
    log "   mosquitto_pub -h localhost -t home/light -m ON"
    log "   mosquitto_pub -h localhost -t home/garage -m OPEN"
    log ""
    log "📁 Logs:"
    log "   Setup : $LOG_FILE"
    log "   Debug : $DEBUG_LOG"
    log "   MQTT  : sudo journalctl -u simpsons-house -f"
    log ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    # Initialise log files (owned by current user, not root)
    echo "Simpson's House Setup v3.3 - $(date)" > "$LOG_FILE"
    echo "Simpson's House Debug Log - $(date)" > "$DEBUG_LOG"

    log "🏠 Starting Simpson's House Setup v3.3..."
    log "📋 Run './install_ca.sh' first if on a corporate network (FortiGate SSL inspection)"
    log ""

    check_root
    sync_system_time
    check_system
    install_packages
    setup_python_env
    configure_mosquitto
    configure_avahi
    setup_systemd_service
    test_mqtt
    display_summary

    log "🎉 Setup complete! Connect your iPad and start controlling the house."
}

trap 'error "Setup failed at line $LINENO — check $DEBUG_LOG"' ERR

main "$@"
