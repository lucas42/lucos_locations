FROM owntracks/frontend:2.15.3

RUN apk add apache2-utils # Needed for htpasswd
COPY config.js /usr/share/nginx/html/config/
COPY _info.json /usr/share/nginx/html/
COPY nginx.tmpl /etc/nginx/nginx.tmpl

COPY startup.sh .
CMD ["./startup.sh"]