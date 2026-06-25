# =============================================================================
# VideoMind Agent - Dockerfile
# =============================================================================
# Build:  docker compose build
# Run:    docker compose up -d
# Test:   curl http://127.0.0.1:8000/health
#
# Default mode: CPU + rule planner (no GPU, no API key required).
# For GPU support, see docs/DEPLOYMENT.md.
# =============================================================================

FROM python:3.10-slim-bookworm

LABEL maintainer="VideoMind Agent"
LABEL description="VideoMind Agent - video content understanding and auto-editing"

# ── System dependencies ──────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ────────────────────────────────────────────────────
COPY backend/ backend/
COPY scripts/ scripts/

# ── Runtime directories ─────────────────────────────────────────────────
RUN mkdir -p /app/data /app/logs

# ── Environment defaults (CPU + rule planner) ──────────────────────────
ENV VIDEOMIND_DEVICE=cpu
ENV VIDEOMIND_PLANNER_PROVIDER=rule
ENV VIDEOMIND_DATA_DIR=/app/data
ENV VIDEOMIND_HOST=0.0.0.0
ENV VIDEOMIND_PORT=8000
ENV VIDEOMIND_MODEL_DIR=/app
ENV VIDEOMIND_DATABASE_URL=sqlite:////app/data/videomind.db
ENV VIDEOMIND_YOLO_MODEL_PATH=yolo11n.pt
ENV VIDEOMIND_MIN_FREE_DISK_GB=5
ENV VIDEOMIND_MAX_UPLOAD_MB=1024
ENV VIDEOMIND_MAX_QUEUE_SIZE=20
ENV VIDEOMIND_WORKER_CONCURRENCY=1
ENV VIDEOMIND_MONITOR_INTERVAL_SEC=30
ENV VIDEOMIND_TASK_TIMEOUT_SEC=3600
ENV DEEPSEEK_API_KEY=
ENV DEEPSEEK_MODEL=deepseek-v4-flash

# ── Health check ────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# ── Expose port ─────────────────────────────────────────────────────────
EXPOSE 8000

# ── Start command ───────────────────────────────────────────────────────
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
