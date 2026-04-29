FROM eclipse-mosquitto:2.0.20
ARG VERSION
ENV VERSION=$VERSION

# Create certreaders group (GID 1500, matches lucos_router) and add mosquitto user to it
# so mosquitto can read TLS private keys from the shared letsencrypt volume
RUN addgroup -g 1500 certreaders && adduser mosquitto certreaders

# inotify-tools provides inotifywait, used by startup.sh to watch for TLS cert
# renewals and send SIGHUP to mosquitto for graceful cert reload
RUN apk add --no-cache inotify-tools

COPY mosquitto.conf /mosquitto/config/
COPY startup.sh .
CMD ["./startup.sh"]
