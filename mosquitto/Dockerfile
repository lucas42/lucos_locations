FROM eclipse-mosquitto:2.0.20

# Create certreaders group (GID 1500, matches lucos_router) and add mosquitto user to it
# so mosquitto can read TLS private keys from the shared letsencrypt volume
RUN addgroup -g 1500 certreaders && adduser mosquitto certreaders

COPY mosquitto.conf /mosquitto/config/
COPY startup.sh .
CMD ["./startup.sh"]
