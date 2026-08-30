# ==============================================================================
# Production Dockerfile for Pipecat Voice Agent
# Supports Groq STT/LLM, Sarvam AI TTS, WebRTC Audio, and Glassmorphism Web UI
# Compatible with Railway, Render, Fly.io, HuggingFace Spaces, and Cloud Run
# ==============================================================================

FROM python:3.12-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PORT=7860

# Install system audio, build tools, and networking libraries
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

# Set working directory
WORKDIR /app

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code, tools, services, and frontend assets
COPY . .

# Expose default port
EXPOSE 7860

# Health check endpoint for cloud orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/status || exit 1

# Start the unified Voice Agent server with dynamic $PORT support
CMD ["sh", "-c", "python server.py --host 0.0.0.0 --port ${PORT}"]
