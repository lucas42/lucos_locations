# Builder stage
# This is used to modify the frontend to add support for antimeridian journeys
# If https://github.com/owntracks/frontend/pull/164 is merged, this can be removed
FROM node:18-alpine AS builder

WORKDIR /app

# Clone the specific version of owntracks/frontend
RUN apk add --no-cache git
RUN git clone --depth 1 --branch v2.15.3 https://github.com/owntracks/frontend.git .

# Install dependencies including the antimeridian fix
RUN npm install
RUN npm install vue-leaflet-antimeridian@1.0.1

# Patch src/views/Map.vue to use the antimeridian-fixed LPolyline
# We use a range-based sed to only remove LPolyline from the vue2-leaflet import block
RUN sed -i '/import {/,/} from "vue2-leaflet";/ { /LPolyline,/d }' src/views/Map.vue && \
    sed -i '/import L from "leaflet";/a import { LPolyline } from "vue-leaflet-antimeridian";' src/views/Map.vue

# Build the application
RUN npm run build

# Final stage
FROM owntracks/frontend:2.15.3

# Copy the built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

RUN apk add --no-cache apache2-utils # Needed for htpasswd
COPY config.js /usr/share/nginx/html/config/
COPY _info.json /usr/share/nginx/html/
COPY nginx.tmpl /etc/nginx/nginx.tmpl

COPY startup.sh .
CMD ["./startup.sh"]