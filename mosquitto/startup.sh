#!/bin/sh
set -e

if [ -z "${RECORDER_USERNAME}" ]; then
	echo "Missing environment variable RECORDER_USERNAME"
	exit 1
fi
if [ -z "${RECORDER_PASSWORD}" ]; then
	echo "Missing environment variable RECORDER_PASSWORD"
	exit 1
fi
if [ -z "${OT_USERNAME}" ]; then
	echo "Missing environment variable OT_USERNAME"
	exit 1
fi
if [ -z "${OT_PASSWORD}" ]; then
	echo "Missing environment variable OT_PASSWORD"
	exit 1
fi

# Fix letsencrypt directory permissions so the mosquitto user can traverse
# to cert files. Certbot creates /etc/letsencrypt/archive/ with mode 0700,
# which blocks non-root users from following the symlinks in live/.
# The privkey files themselves are group-readable (certreaders GID 1500).
find /etc/letsencrypt -type d -exec chmod o+rx {} \; 2>/dev/null || true

touch /mosquitto/config/passwords
chown mosquitto:mosquitto /mosquitto/config/passwords
chmod 0600 /mosquitto/config/passwords
mosquitto_passwd -b /mosquitto/config/passwords $RECORDER_USERNAME $RECORDER_PASSWORD
mosquitto_passwd -b /mosquitto/config/passwords $OT_USERNAME $OT_PASSWORD

mosquitto -c /mosquitto/config/mosquitto.conf
