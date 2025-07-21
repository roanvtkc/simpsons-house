#!/bin/bash
set -e

# Improved TKC Wireless CA Certificate Installer
# Installs FortiGate certificate for environments with certificate inspection

# Configuration
CERT_PATH="/usr/local/share/ca-certificates/wirelesstkc.crt"
DOWNLOAD_URL="http://10.20.1.83:8081/wirelesstkc.pem"
BACKUP_PATH="/usr/local/share/ca-certificates/wirelesstkc.crt.backup"
LOG_PREFIX="[CA Install]"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}${LOG_PREFIX}${NC} $1"
}

warn() {
    echo -e "${YELLOW}${LOG_PREFIX} WARNING:${NC} $1"
}

error() {
    echo -e "${RED}${LOG_PREFIX} ERROR:${NC} $1"
}

# Check if certificate is already installed
check_existing_certificate() {
    if grep -q "wirelesstkc" /etc/ssl/certs/ca-certificates.crt 2>/dev/null; then
        log "TKC FortiGate CA certificate is already installed in the trust store."
        return 0
    fi
    return 1
}

# Check internet connectivity to certificate server
check_connectivity() {
    log "Testing connectivity to certificate server..."
    
    if ! ping -c 1 -W 5 10.20.1.83 >/dev/null 2>&1; then
        warn "Cannot reach certificate server (10.20.1.83)"
        warn "You may not be on the TKC network or the server may be down"
        return 1
    fi
    
    log "Certificate server is reachable"
    return 0
}

# Download and verify certificate
download_certificate() {
    log "Downloading TKC Wireless CA certificate from $DOWNLOAD_URL..."
    
    # Create temporary file for download
    local temp_cert="/tmp/wirelesstkc_temp.pem"
    
    # Download with timeout and user agent
    if ! sudo wget --timeout=30 --tries=3 \
                   --user-agent="Simpson's House Setup" \
                   "$DOWNLOAD_URL" -O "$temp_cert" 2>/dev/null; then
        error "Failed to download certificate from $DOWNLOAD_URL"
        error "Please check:"
        error "  - You are connected to the TKC network"
        error "  - The certificate server is accessible"
        error "  - The URL is correct: $DOWNLOAD_URL"
        return 1
    fi
    
    # Verify it's actually a certificate file
    if ! openssl x509 -in "$temp_cert" -text -noout >/dev/null 2>&1; then
        error "Downloaded file is not a valid X.509 certificate"
        rm -f "$temp_cert"
        return 1
    fi
    
    # Backup existing certificate if it exists
    if [ -f "$CERT_PATH" ]; then
        log "Backing up existing certificate to $BACKUP_PATH"
        sudo cp "$CERT_PATH" "$BACKUP_PATH"
    fi
    
    # Move certificate to final location
    sudo mv "$temp_cert" "$CERT_PATH"
    sudo chmod 644 "$CERT_PATH"
    sudo chown root:root "$CERT_PATH"
    
    log "Certificate saved to $CERT_PATH"
    return 0
}

# Update system certificate trust store
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

# Verify certificate installation
verify_installation() {
    log "Verifying certificate installation..."
    
    # Check if certificate appears in trust store
    if grep -q "wirelesstkc" /etc/ssl/certs/ca-certificates.crt 2>/dev/null; then
        log "✅ TKC FortiGate CA certificate successfully installed"
        
        # Show certificate details
        log "Certificate details:"
        if openssl x509 -in "$CERT_PATH" -subject -issuer -dates -noout 2>/dev/null; then
            return 0
        else
            warn "Certificate installed but cannot read details"
            return 0
        fi
    else
        error "Certificate installation verification failed"
        return 1
    fi
}

# Cleanup function
cleanup() {
    # Remove any temporary files
    rm -f /tmp/wirelesstkc_temp.pem
}

# Main installation function
main() {
    log "Starting TKC Wireless CA certificate installation..."
    
    # Set cleanup trap
    trap cleanup EXIT
    
    # Check if already installed
    if check_existing_certificate; then
        log "Certificate installation not needed"
        return 0
    fi
    
    log "TKC FortiGate CA certificate not found, installing..."
    
    # Check connectivity
    if ! check_connectivity; then
        error "Cannot proceed without network connectivity to certificate server"
        return 1
    fi
    
    # Download certificate
    if ! download_certificate; then
        error "Certificate download failed"
        return 1
    fi
    
    # Update trust store
    if ! update_trust_store; then
        error "Trust store update failed"
        return 1
    fi
    
    # Verify installation
    if ! verify_installation; then
        error "Certificate verification failed"
        return 1
    fi
    
    log "🎉 TKC FortiGate CA certificate installation completed successfully!"
    log "Your system can now access HTTPS sites through FortiGate inspection"
    
    return 0
}

# Run main function only if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
