#!/bin/bash
set -e

# Helper to install the TKC Wireless CA certificate
CERT_PATH="/usr/local/share/ca-certificates/wirelesstkc.crt"
DOWNLOAD_URL="http://10.20.1.83:8081/wirelesstkc.pem"

# Only install if the CA is missing from the system trust store
if ! grep -q "wirelesstkc" /etc/ssl/certs/ca-certificates.crt; then
    echo "Downloading TKC Wireless CA certificate..."
    sudo wget "$DOWNLOAD_URL" -O "$CERT_PATH"
    echo "Updating CA trust store..."
    sudo update-ca-certificates
else
    echo "TKC FortiGate CA is already present in the trust store."
fi
