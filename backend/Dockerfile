# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TF_CPP_MIN_LOG_LEVEL=2

WORKDIR /app

# System deps:
#   libjpeg / zlib  -> Pillow
#   libgl1 / libglib2.0-0 -> opencv-python-headless (libGL needed by some cv2 ops)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
# Optional: bake the weights into the image. Skip this line if you'd rather
# mount the file at runtime (see README "Cloud deployment" section).
# Comment this back in when you've placed the file under backend/models/.
COPY models ./models

# Non-root user for safety.
RUN useradd --create-home --uid 10001 leafscan \
    && chown -R leafscan:leafscan /app
USER leafscan

EXPOSE 8000

# Render/Railway/Fly all set $PORT. Fall back to 8000 for local runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
