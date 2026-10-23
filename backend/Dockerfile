# ==============================================================================
# DOCKERFILE BACKEND - debateIA (Optimizado para Hetzner Cloud CPU)
# ==============================================================================
FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4

WORKDIR /app

# Instalar dependencias de sistema esenciales para audio (libsndfile, ffmpeg) y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalar dependencias Python
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Copiar código fuente
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-ping-interval", "20", "--ws-ping-timeout", "20"]
