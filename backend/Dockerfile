FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 skillforge \
    && useradd --uid 10001 --gid skillforge --no-create-home --shell /usr/sbin/nologin skillforge \
    && mkdir -p /data/media /staticfiles \
    && touch /data/.keep /staticfiles/.keep \
    && chown -R skillforge:skillforge /data /staticfiles
COPY backend/ ./
COPY infra/docker/start-api.sh infra/docker/healthcheck.py /app/infra/docker/
# Checkouts made on Windows must also work as Linux container entrypoints.
RUN sed -i 's/\r$//' /app/infra/docker/start-api.sh \
    && chmod 755 /app/infra/docker/start-api.sh
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/app/infra/docker/start-api.sh"]
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "--threads=4", "--url-scheme=https", "--channel-timeout=300", "--max-request-body-size=12582912", "config.wsgi:application"]
