#!/bin/bash
set -e

# TKC FortiGate CA Certificate Installer
# Installs the FortiGate CA so HTTPS works through TKC SSL inspection
#
# Also ensures the system clock is correct — a wrong clock causes
# FortiGate's dynamically-signed interception certs to appear "not yet valid",
# which breaks HTTPS even after the CA cert is installed.

# Configuration
CERT_PATH="/usr/local/share/ca-certificates/wirelesstkc.crt"
DOWNLOAD_URL="http://10.20.1.83:8081/wirelesstkc.pem"
BACKUP_PATH="/usr/local/share/ca-certificates/wirelesstkc.crt.backup"
CERT_SERVER="10.20.1.83"
LOG_PREFIX="[CA Install]"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}${LOG_PREFIX}${NC} $1"; }
warn() { echo -e "${YELLOW}${LOG_PREFIX} WARNING:${NC} $1"; }
error(){ echo -e "${RED}${LOG_PREFIX} ERROR:${NC} $1"; }

# -----------------------------------------------------------------------------
# STEP 0 — System clock sync
# -----------------------------------------------------------------------------
# A fresh Pi often has a stale or zeroed RTC. FortiGate signs interception
# certs with today's date, so if the Pi's clock is behind, those certs will
# fail validation with "certificate is not yet valid" — even if the CA is
# correctly installed. We fix the clock first so verification always works.

sync_system_time() {
    log "Checking system clock..."
    log "Current Pi time: $(date)"

    # Point timesyncd at reliable servers and restart it
    log "Configuring NTP servers..."
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

    warn "NTP sync not confirmed (NTP may be blocked on this network)."
    warn "Trying HTTP date header fallback from cert server..."

    # Many corporate proxies/servers include a Date: header we can use
    local http_date
    http_date=$(curl -sI --max-time 5 "http://${CERT_SERVER}:8081/" 2>/dev/null \
                | grep -i "^Date:" | sed 's/[Dd]ate: //' | tr -d '\r\n')

    if [ -n "$http_date" ]; then
        sudo date -s "$http_date" >/dev/null 2>&1
        log "✅ Clock set via HTTP header: $(date)"
        return 0
    fi

    warn "Could not sync clock automatically."
    warn "Current Pi time: $(date)"
    warn "If HTTPS verification fails below, run: sudo date -s 'YYYY-MM-DD HH:MM:SS'"
    # Non-fatal — continue and let verification report if there's still a problem
    return 0
}

# -----------------------------------------------------------------------------
# Certificate installation steps
# -----------------------------------------------------------------------------

check_existing_certificate() {
    if grep -q "wirelesstkc" /etc/ssl/certs/ca-certificates.crt 2>/dev/null; then
        log "TKC FortiGate CA certificate is already installed in the trust store."
        return 0
    fi
    return 1
}

check_connectivity() {
    log "Testing connectivity to certificate server..."
    if ! ping -c 1 -W 5 "${CERT_SERVER}" >/dev/null 2>&1; then
        warn "Cannot reach certificate server (${CERT_SERVER})"
        warn "You may not be on the TKC network or the server may be down"
        return 1
    fi
    log "Certificate server is reachable"
    return 0
}

download_certificate() {
    log "Downloading TKC Wireless CA certificate from $DOWNLOAD_URL..."

    local temp_cert="/tmp/wirelesstkc_temp.pem"

    if ! sudo wget --timeout=30 --tries=3 \
                   --user-agent="Simpson's House Setup" \
                   "$DOWNLOAD_URL" -O "$temp_cert" 2>/dev/null; then
        error "Failed to download certificate from $DOWNLOAD_URL"
        error "Check: TKC network connected, cert server accessible, URL correct"
        return 1
    fi

    if ! openssl x509 -in "$temp_cert" -text -noout >/dev/null 2>&1; then
        error "Downloaded file is not a valid X.509 certificate"
        rm -f "$temp_cert"
        return 1
    fi

    if [ -f "$CERT_PATH" ]; then
        log "Backing up existing certificate to $BACKUP_PATH"
        sudo cp "$CERT_PATH" "$BACKUP_PATH"
    fi

    sudo mv "$temp_cert" "$CERT_PATH"
    sudo chmod 644 "$CERT_PATH"
    sudo chown root:root "$CERT_PATH"

    log "Certificate saved to $CERT_PATH"
    return 0
}

update_trust_store() {
    log "Updating system certificate trust store..."
    if sudo update-ca-certificates 2>/dev/null; then
        log "Certificate trust store updated successfully"
        return 0
    else
        error "Failed to update certificate trust store"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# STEP LAST — Deep verification
# -----------------------------------------------------------------------------
# Checks both the trust store AND makes a real HTTPS connection to GitHub.
# This catches clock-skew problems that a grep-only check misses.

verify_installation() {
    log "Verifying certificate installation..."

    # 1. Trust store check
    if ! grep -q "wirelesstkc" /etc/ssl/certs/ca-certificates.crt 2>/dev/null; then
        error "Certificate not found in trust store after update"
        return 1
    fi
    log "✅ Certificate found in trust store"

    # 2. Show cert details for confirmation
    log "Certificate details:"
    openssl x509 -in "$CERT_PATH" -subject -issuer -dates -noout 2>/dev/null || true

    # 3. Real HTTPS test — this is where clock-skew failures surface
    log "Testing live HTTPS connection to GitHub..."
    if curl -sf --max-time 15 https://github.com > /dev/null 2>&1; then
        log "✅ HTTPS to GitHub successful"
        return 0
    fi

    # 4. Diagnose clock-skew if HTTPS failed
    error "HTTPS test failed. Diagnosing..."
    log "Current system time: $(date)"

    local curl_err
    curl_err=$(curl -sf --max-time 15 https://github.com 2>&1 || true)
    log "curl error: $curl_err"

    if echo "$curl_err" | grep -q "not yet valid\|certificate has expired\|certificate verify"; then
        error "This looks like a clock problem. System time may still be wrong."
        error "Current time: $(date)"
        error "Try running:  sudo date -s '\$(curl -sI http://${CERT_SERVER}:8081/ | grep -i date | cut -d' ' -f2-)'"
    fi

    error "Certificate installed but live HTTPS verification failed."
    error "Check the Logs above for the specific error."
    return 1
}

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

cleanup() {
    rm -f /tmp/wirelesstkc_temp.pem
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    log "Starting TKC FortiGate CA certificate installation..."
    trap cleanup EXIT

    # Always sync the clock first — a wrong clock breaks HTTPS even with
    # the right CA cert installed (FortiGate issues certs dated "today")
    sync_system_time

    if check_existing_certificate; then
        log "Certificate already installed — running live HTTPS verification..."
        verify_installation
        return $?
    fi

    log "TKC FortiGate CA certificate not found, installing..."

    if ! check_connectivity; then
        error "Cannot proceed without network connectivity to certificate server"
        return 1
    fi

    if ! download_certificate; then
        error "Certificate download failed"
        return 1
    fi

    if ! update_trust_store; then
        error "Trust store update failed"
        return 1
    fi

    if ! verify_installation; then
        return 1
    fi

    log "🎉 TKC FortiGate CA certificate installation completed successfully!"
    log "Your Pi can now access HTTPS sites through FortiGate SSL inspection"
    return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
