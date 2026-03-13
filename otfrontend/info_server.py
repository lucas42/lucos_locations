import http.server
import json
import ssl
import socket
import struct
import datetime
import os

PORT = 8080
MQTT_HOST = os.environ.get('MQTT_HOST', 'mqtt')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '8883'))

# Hardcoded system information
INFO_BASE = {
    "system": "lucos_locations",
    "ci": {
        "circle": "gh/lucas42/lucos_locations"
    }
}

class InfoHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/_info':
            self.handle_info()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_info(self):
        info = INFO_BASE.copy()
        info['checks'] = {}
        info['metrics'] = {}

        expiry_seconds = self.get_tls_expiry()

        # 20 days = 20 * 24 * 60 * 60 seconds
        check_ok = expiry_seconds is not None and expiry_seconds > (20 * 24 * 60 * 60)

        info['checks']['mosquitto-tls'] = {
            "techDetail": "Checks whether the TLS Certificate on the mosquitto server is valid and not about to expire",
            "ok": check_ok
        }
        if not check_ok:
            if expiry_seconds is None:
                info['checks']['mosquitto-tls']['debug'] = "Failed to fetch TLS certificate"
            else:
                info['checks']['mosquitto-tls']['debug'] = f"TLS Certificate due to expire in {expiry_seconds} seconds"

        info['metrics']['mosquitto-tls-expiry'] = {
            "value": expiry_seconds if expiry_seconds is not None else -1,
            "techDetail": "The number of seconds until the mosquitto TLS Certification expires"
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(info).encode('utf-8'))

    def get_tls_expiry(self):
        try:
            # Connect to mosquitto via TLS and perform a proper MQTT handshake.
            # A bare TLS connection (no MQTT data) causes mosquitto to log "protocol error"
            # on every poll. Sending a valid MQTT CONNECT packet instead causes mosquitto
            # to log "disconnected, not authorised" — a normal informational entry.
            # CERT_OPTIONAL: parses the peer cert without requiring chain verification
            # (MQTT_HOST is an internal Docker service name, not in the cert's SAN).
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_OPTIONAL
            with socket.create_connection((MQTT_HOST, MQTT_PORT), timeout=2) as raw:
                with ctx.wrap_socket(raw, server_hostname=MQTT_HOST) as tls:
                    # Read the cert during the TLS handshake
                    cert = tls.getpeercert()

                    # Build MQTT 3.1.1 CONNECT packet
                    client_id = b'lucos-healthcheck'
                    variable_header = (
                        b'\x00\x04MQTT'  # Protocol name
                        b'\x04'          # Protocol level (3.1.1)
                        b'\x00'          # Connect flags (no clean session, no will, no auth)
                        b'\x00\x00'      # Keepalive: 0 seconds
                    )
                    # Payload: client ID as UTF-8 prefixed string
                    payload = struct.pack('!H', len(client_id)) + client_id
                    remaining = variable_header + payload
                    connect_pkt = bytes([0x10, len(remaining)]) + remaining

                    tls.sendall(connect_pkt)

                    # Read CONNACK (4 bytes: fixed header 2 + variable header 2)
                    tls.recv(4)

                    # Send DISCONNECT packet so mosquitto closes cleanly
                    tls.sendall(bytes([0xe0, 0x00]))

            not_after = cert.get('notAfter')
            if not_after:
                expiry_date = datetime.datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                return int((expiry_date - now).total_seconds())
        except Exception as e:
            print(f"Error checking TLS: {e}")
        return None

if __name__ == '__main__':
    # ThreadingHTTPServer is better for production-like use in low-traffic scenarios
    http.server.ThreadingHTTPServer(('', PORT), InfoHandler).serve_forever()
