import http.server
import json
import ssl
import socket
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
            # Use ssl module for a pure TLS connection — no MQTT handshake, so mosquitto
            # won't log protocol errors (unlike openssl s_client which triggered them on
            # every /_info poll).
            # CERT_OPTIONAL: parses the peer certificate without requiring chain
            # verification to succeed (needed since MQTT_HOST is an internal name).
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_OPTIONAL
            with socket.create_connection((MQTT_HOST, MQTT_PORT), timeout=2) as raw:
                with ctx.wrap_socket(raw, server_hostname=MQTT_HOST) as tls:
                    cert = tls.getpeercert()
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
