#!/bin/sh
set -e

htpasswd -cbB /etc/nginx/owntracks.htpasswd $OT_USERNAME $OT_PASSWORD

envsubst '\${SERVER_HOST} \${SERVER_PORT} \${LISTEN_PORT}'  < /etc/nginx/nginx.tmpl > /etc/nginx/nginx.conf
python3 /app/info_server.py &
nginx -g 'daemon off;'