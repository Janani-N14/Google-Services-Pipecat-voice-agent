# ==============================================================================
# Ultra-Lightweight Production Dockerfile for Pipecat Voice Agent
# Uses CPU-only PyTorch build to reduce image size from 4.5GB to ~380MB
# ==============================================================================

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PORT=7860

# Install minimal audio & networking libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libasound2 \
    libasound2-dev \
    libportaudio2 \
    portaudio19-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: Install lightweight CPU-only PyTorch (prevents huge 3.5GB CUDA download)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install remaining application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 3: Copy application source code
COPY . .

EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/status || exit 1

CMD ["sh", "-c", "python server.py --host 0.0.0.0 --port ${PORT}"]
