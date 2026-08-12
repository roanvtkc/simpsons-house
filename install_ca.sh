#!/bin/bash
set -e

# TKC FortiGate CA Certificate Installer
# Installs the FortiGate CA so HTTPS works through TKC SSL inspection
#
# Also ensures the system clock is correct — a wrong clock causes
# FortiGate's dynamically-signed interception certs to appear "not yet valid",
# which breaks HTTPS even after the CA cert is installed.

# Configuration
#
# NOTE: this must be the FortiGate SSL-inspection CA (O=Fortinet), NOT
# wirelesstkc.pem. That file is the 802.1X/RADIUS server certificate for
# wireless.tkc.wa.edu.au — a self-signed *leaf*, not a CA. Installing it
# does nothing for SSL inspection, which is what broke pip installs.
CERT_PATH="/usr/local/share/ca-certificates/tkc-fortigate-ca.crt"
DOWNLOAD_URL="http://10.20.1.83:8081/fortigate.crt"
BACKUP_PATH="/usr/local/share/ca-certificates/tkc-fortigate-ca.crt.backup"
CERT_SERVER="10.20.1.83"
LOG_PREFIX="[CA Install]"

# Expected CA identity. The structural checks (self-signed, CA:TRUE, O=Fortinet)
# are enforced; the fingerprint is advisory and only warns on mismatch, so a
# FortiGate replacement doesn't hard-fail the installer.
EXPECTED_CA_ORG="Fortinet"
EXPECTED_FINGERPRINT="EB:81:07:CC:EF:5A:27:A7:0A:02:CD:97:E7:E3:EB:04:48:62:17:BE:3C:3D:82:1A:EE:DA:CA:F0:2E:CB:FC:B9"

# A host that IS subject to SSL inspection, used for the live verification test.
# Do not use github.com here — it is exempt from deep inspection at TKC, so it
# succeeds even when the CA is missing and hides the failure.
VERIFY_URL="https://pypi.org/simple/"

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

# Validate that a PEM file really is the FortiGate SSL-inspection CA.
# Used both on the freshly downloaded file and on the already-installed one.
is_fortigate_ca() {
    local cert="$1"

    [ -f "$cert" ] || return 1
    openssl x509 -in "$cert" -noout >/dev/null 2>&1 || return 1

    # Must be a CA, not a leaf. This is the check that would have caught
    # wirelesstkc.pem being installed here.
    if ! openssl x509 -in "$cert" -noout -text 2>/dev/null \
         | grep -A1 "X509v3 Basic Constraints" | grep -q "CA:TRUE"; then
        return 1
    fi

    # Must be self-signed (subject == issuer) — it's a root.
    local subj issuer
    subj=$(openssl x509 -in "$cert" -noout -subject 2>/dev/null | sed 's/^subject=//')
    issuer=$(openssl x509 -in "$cert" -noout -issuer 2>/dev/null | sed 's/^issuer=//')
    [ "$subj" = "$issuer" ] || return 1

    # Must be the FortiGate's CA specifically.
    echo "$subj" | grep -q "O *= *${EXPECTED_CA_ORG}" || return 1

    return 0
}

check_existing_certificate() {
    # NOTE: grep-ing ca-certificates.crt for a name will never work —
    # PEM bundle data is base64-encoded binary, not readable text.
    #
    # `openssl verify` alone is ALSO not enough: it returns OK for *any*
    # self-signed cert already present in the trust store, so a wrong cert
    # sitting at CERT_PATH reports "already installed" forever. We check the
    # cert's identity as well as its trust status.
    if ! is_fortigate_ca "$CERT_PATH"; then
        return 1
    fi

    if ! openssl verify "$CERT_PATH" >/dev/null 2>&1; then
        return 1
    fi

    log "TKC FortiGate CA certificate is already installed and trusted."
    return 0
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
    log "Downloading TKC FortiGate SSL-inspection CA from $DOWNLOAD_URL..."

    local temp_cert="/tmp/tkc_fortigate_ca_temp.pem"

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

    # Confirm we got the SSL-inspection CA and not some other cert the
    # server happens to publish (e.g. wirelesstkc.pem, a self-signed leaf).
    if ! is_fortigate_ca "$temp_cert"; then
        error "Downloaded certificate is not the FortiGate SSL-inspection CA"
        error "Expected a self-signed CA with O=${EXPECTED_CA_ORG}, got:"
        openssl x509 -in "$temp_cert" -noout -subject -issuer 2>&1 | sed 's/^/    /'
        rm -f "$temp_cert"
        return 1
    fi

    local got_fp
    got_fp=$(openssl x509 -in "$temp_cert" -noout -fingerprint -sha256 2>/dev/null | cut -d= -f2)
    if [ "$got_fp" != "$EXPECTED_FINGERPRINT" ]; then
        warn "CA fingerprint differs from the expected value."
        warn "  expected: $EXPECTED_FINGERPRINT"
        warn "  got:      $got_fp"
        warn "This is expected if the FortiGate was replaced or its CA reissued."
        warn "Confirm against the firewall, then update EXPECTED_FINGERPRINT in this script."
    else
        log "CA fingerprint matches expected value"
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
    # Use --fresh to do a full rebuild — avoids the "0 added" stale-symlink
    # problem where leftover symlinks from a previous run fool update-ca-certificates
    # into skipping the cert even though it isn't in the bundle yet.
    if sudo update-ca-certificates --fresh 2>/dev/null; then
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

    # 0. Identity check — make sure CERT_PATH holds the FortiGate CA at all.
    if ! is_fortigate_ca "$CERT_PATH"; then
        error "$CERT_PATH is not the FortiGate SSL-inspection CA"
        return 1
    fi

    # 1. Trust store check — use openssl verify, NOT grep.
    # ca-certificates.crt is a PEM bundle of base64-encoded binary data;
    # cert names never appear as readable text inside it.
    if ! openssl verify "$CERT_PATH" >/dev/null 2>&1; then
        error "Certificate not trusted by system store (openssl verify failed)"
        error "Trying a full trust store rebuild..."
        sudo update-ca-certificates --fresh 2>/dev/null || true
        if ! openssl verify "$CERT_PATH" >/dev/null 2>&1; then
            error "Certificate still not trusted after rebuild"
            return 1
        fi
    fi
    log "✅ Certificate is trusted by system store"

    # 2. Show cert details for confirmation
    log "Certificate details:"
    openssl x509 -in "$CERT_PATH" -subject -issuer -dates -noout 2>/dev/null || true

    # 3. Real HTTPS test against an SSL-INSPECTED host.
    # github.com is exempt from deep inspection at TKC and presents a genuine
    # public chain, so testing it passes even with no CA installed — that is
    # exactly how a broken install previously reported success while every
    # Python package index still failed.
    log "Testing live HTTPS connection to ${VERIFY_URL} (SSL-inspected)..."
    if curl -sf --max-time 15 "$VERIFY_URL" > /dev/null 2>&1; then
        log "✅ HTTPS through SSL inspection successful"

        # pip on Debian/Raspberry Pi OS uses the system trust store via its
        # vendored certifi, so curl succeeding is a good sign — but verify with
        # Python directly, since that is what actually runs pip.
        #
        # We clear VERIFY_X509_STRICT to mirror pip. Python 3.13 turns strict
        # RFC 5280 checking on by default in ssl.create_default_context(), and
        # the FortiGate CA has no Authority Key Identifier extension, so strict
        # mode rejects it. pip is unaffected because urllib3 builds its own
        # context without that flag. See the warning below.
        log "Verifying Python/pip can validate the inspected connection..."
        if python3 - <<'PYEOF' >/dev/null 2>&1
import socket, ssl, sys
ctx = ssl.create_default_context()
ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
with socket.create_connection(("pypi.org", 443), 15) as sock:
    with ctx.wrap_socket(sock, server_hostname="pypi.org"):
        pass
PYEOF
        then
            log "✅ Python TLS verification successful — pip installs will work"
        else
            warn "Python could not verify the connection even though curl could."
            warn "If pip still fails, check for a stale venv or a PIP_CERT override."
        fi

        # Heads-up for anything that is NOT pip.
        if ! python3 -c "import urllib.request; urllib.request.urlopen('${VERIFY_URL}', timeout=15)" >/dev/null 2>&1; then
            warn "Note: Python's stdlib urllib/requests still reject this CA under"
            warn "VERIFY_X509_STRICT (on by default from Python 3.13) because the"
            warn "FortiGate CA omits the Authority Key Identifier extension."
            warn "pip, curl and git are unaffected. If you write Python that makes"
            warn "HTTPS calls on this Pi, clear ssl.VERIFY_X509_STRICT on the context."
        fi
        return 0
    fi

    # 4. Diagnose clock-skew if HTTPS failed
    error "HTTPS test failed. Diagnosing..."
    log "Current system time: $(date)"

    # -sS (not -sf) so curl prints the actual TLS error instead of staying silent.
    local curl_err
    curl_err=$(curl -sS --max-time 15 -o /dev/null "$VERIFY_URL" 2>&1 || true)
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
    rm -f /tmp/tkc_fortigate_ca_temp.pem
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
