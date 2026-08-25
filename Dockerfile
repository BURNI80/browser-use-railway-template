FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="browser-use-railway" \
      org.opencontainers.image.description="Self-hosted Browser Use API + UI for Railway" \
      org.opencontainers.image.source="https://github.com/browser-use/browser-use"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONIOENCODING=UTF-8 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    IN_DOCKER=true \
    ANONYMIZED_TELEMETRY=false \
    BROWSER_USE_CLOUD_SYNC=false \
    BROWSER_USE_VERSION_CHECK=false

RUN apt-get update -qq \
    && apt-get install -qq -y --no-install-recommends \
        ca-certificates \
        chromium \
        fonts-liberation \
        fonts-noto-core \
        fonts-unifont \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/chromium /usr/bin/chromium-browser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY static ./static

RUN useradd --create-home --uid 1000 browseruse \
    && mkdir -p /data/config /data/downloads /home/browseruse/.config \
    && ln -s /data/config /home/browseruse/.config/browseruse \
    && chown -R browseruse:browseruse /app /data /home/browseruse

USER browseruse

ENV HOME=/home/browseruse \
    BROWSER_USE_CONFIG_DIR=/home/browseruse/.config/browseruse \
    BU_DATA_DIR=/data

EXPOSE 8000

CMD ["sh", "-c", "mkdir -p /data/config /data/downloads && exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
