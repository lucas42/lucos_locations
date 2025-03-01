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

touch /mosquitto/config/passwords
chown root:root /mosquitto/config/passwords
chmod 0700 /mosquitto/config/passwords
mosquitto_passwd -b /mosquitto/config/passwords $RECORDER_USERNAME $RECORDER_PASSWORD
mosquitto_passwd -b /mosquitto/config/passwords $OT_USERNAME $OT_PASSWORD

mosquitto -c /mosquitto/config/mosquitto.conf