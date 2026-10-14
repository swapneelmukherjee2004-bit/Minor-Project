FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt && playwright install --with-deps chromium
COPY backend/ .
COPY dataset/ /dataset/
ENV HOST=0.0.0.0 PORT=8000
ENV DATASET_DIR=/dataset STORAGE_DIR=/data/screenshots BROWSER_NO_SANDBOX=true
RUN useradd -m app && mkdir -p /data/screenshots && chown -R app /data
# Chromium runs with --no-sandbox because container root/seccomp often lacks user namespaces; the container itself is the sandbox.
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host $HOST --port $PORT"]
