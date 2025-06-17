#!/bin/bash
# Install the TKC Wireless CA certificate used on some TKC networks.
# This resolves HTTPS errors like "server certificate verification failed" when
# running apt or git.
set -e

CERT_PATH="/usr/local/share/ca-certificates/wirelesstkc.crt"

if [ ! -f "$CERT_PATH" ]; then
    echo "Downloading TKC Wireless CA certificate..."
    sudo wget http://10.20.1.206/updates/wirelesstkc.pem -O "$CERT_PATH"
    echo "Updating CA trust store..."
    sudo update-ca-certificates
fi

grep -R "wirelesstkc" /etc/ssl/certs/ca-certificates.crt && \
    echo "CA installed successfully"
