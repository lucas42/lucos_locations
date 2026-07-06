import http.server
import json
import ssl
import socket
import struct
import datetime
import os
import urllib.request

PORT = 8080
MQTT_HOST = os.environ.get('MQTT_HOST', 'mqtt')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '8883'))
HEALTHCHECK_USERNAME = os.environ.get('HEALTHCHECK_USERNAME', '')
HEALTHCHECK_PASSWORD = os.environ.get('HEALTHCHECK_PASSWORD', '')
# Same host/port nginx already proxies /owntracks/api/ to (see nginx.tmpl)
SERVER_HOST = os.environ.get('SERVER_HOST', 'otrecorder')
SERVER_PORT = int(os.environ.get('SERVER_PORT', '8083'))

# 30 hours: long enough to tolerate a normal period of inactivity (e.g. overnight,
# or significant-change mode not triggering), short enough to catch a multi-day
# silent gap within a day or two of it starting.
LOCATION_FRESHNESS_THRESHOLD_SECONDS = 30 * 60 * 60

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

        age_seconds = self.get_location_age_seconds()

        freshness_ok = age_seconds is not None and age_seconds < LOCATION_FRESHNESS_THRESHOLD_SECONDS

        info['checks']['location-freshness'] = {
            "techDetail": "Checks that fresh location data has been recorded recently, to catch silent gaps (e.g. a stopped client or broken ingestion) that a service-up healthcheck alone wouldn't detect",
            "ok": freshness_ok
        }
        if not freshness_ok:
            if age_seconds is None:
                info['checks']['location-freshness']['debug'] = "Failed to fetch last recorded location data from the recorder"
            else:
                info['checks']['location-freshness']['debug'] = f"Last recorded location data is {age_seconds} seconds old"

        info['metrics']['location-data-age-seconds'] = {
            "value": age_seconds if age_seconds is not None else -1,
            "techDetail": "The number of seconds since the most recent location fix recorded, across all devices"
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(info).encode('utf-8'))

    def get_tls_expiry(self):
        try:
            # Connect to mosquitto via TLS and perform a proper MQTT handshake.
            # A bare TLS connection (no MQTT data) causes mosquitto to log "protocol error"
            # on every poll. Sending a valid MQTT CONNECT packet with credentials allows
            # a clean connect/disconnect without any error log entries.
            # CERT_OPTIONAL: parses the peer cert without requiring chain verification
            # (MQTT_HOST is an internal Docker service name, not in the cert's SAN).
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_OPTIONAL
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            with socket.create_connection((MQTT_HOST, MQTT_PORT), timeout=2) as raw:
                with ctx.wrap_socket(raw, server_hostname=MQTT_HOST) as tls:
                    # Read the cert during the TLS handshake
                    cert = tls.getpeercert()

                    # Build MQTT 3.1.1 CONNECT packet with username/password auth
                    client_id = b'lucos-healthcheck'
                    username = HEALTHCHECK_USERNAME.encode('utf-8')
                    password = HEALTHCHECK_PASSWORD.encode('utf-8')
                    variable_header = (
                        b'\x00\x04MQTT'  # Protocol name
                        b'\x04'          # Protocol level (3.1.1)
                        b'\xC2'          # Connect flags: username(7)+password(6)+cleanSession(1)
                        b'\x00\x00'      # Keepalive: 0 seconds
                    )
                    # Payload: client ID, username, password — each as a UTF-8 prefixed string
                    payload = (
                        struct.pack('!H', len(client_id)) + client_id +
                        struct.pack('!H', len(username)) + username +
                        struct.pack('!H', len(password)) + password
                    )
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

    def get_location_age_seconds(self):
        try:
            url = f"http://{SERVER_HOST}:{SERVER_PORT}/api/0/last"
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read())

            # The recorder returns a JSON array of per-device location objects
            # (each with a "tst" unix timestamp) when it has data, or an empty
            # object "{}" when it has none.
            if not isinstance(data, list) or not data:
                return None

            timestamps = [entry['tst'] for entry in data if isinstance(entry, dict) and 'tst' in entry]
            if not timestamps:
                return None

            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            return int(now - max(timestamps))
        except Exception as e:
            print(f"Error checking location freshness: {e}")
        return None

if __name__ == '__main__':
    # ThreadingHTTPServer is better for production-like use in low-traffic scenarios
    http.server.ThreadingHTTPServer(('', PORT), InfoHandler).serve_forever()
