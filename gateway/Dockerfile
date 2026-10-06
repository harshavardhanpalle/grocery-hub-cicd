FROM nginxinc/nginx-unprivileged:1.27-alpine
# Apply Alpine security patches (needs root), then drop back to the non-root nginx user (uid 101)
USER root
RUN apk update && apk upgrade --no-cache
USER 101
COPY gateway/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO /dev/null http://127.0.0.1:8080/healthz || exit 1
