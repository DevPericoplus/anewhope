FROM python:3.12-slim
WORKDIR /app
COPY nginx_monitor /app/nginx_monitor
ENV PYTHONUNBUFFERED=1 \
    NGINX_MONITOR_DB=/data/nginx_monitor/nginx.db \
    NGINX_MONITOR_LOG=/var/log/nginx/monitor.json \
    NGINX_STATUS_URL=http://nginx:8088/nginx_status \
    NGINX_MONITOR_LISTEN=0.0.0.0:8096
# Mismo sello que el resto de imágenes de anewhope: Push_Artifacts
# compara /app/.anewhope_build_sha con el HEAD de util01.
ARG ANEWHOPE_BUILD_SHA=unknown
RUN printf '%s\n' "$ANEWHOPE_BUILD_SHA" > /app/.anewhope_build_sha
EXPOSE 8096
CMD ["python", "-m", "nginx_monitor"]
