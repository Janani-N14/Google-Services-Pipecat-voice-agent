/**
 * Web Audio API Frequency & Waveform Visualizer
 * Renders glowing audio reactive bars on HTML5 Canvas.
 */

class AudioVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.audioCtx = null;
    this.analyser = null;
    this.source = null;
    this.dataArray = null;
    this.animationId = null;
    this.isActive = false;

    if (this.canvas) {
      this.resize();
      window.addEventListener('resize', () => this.resize());
    }
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * (window.devicePixelRatio || 1);
    this.canvas.height = rect.height * (window.devicePixelRatio || 1);
    if (this.ctx) {
      this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    }
  }

  connectStream(mediaStream) {
    try {
      if (!this.audioCtx) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        this.audioCtx = new AudioContextClass();
      }

      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }

      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 64;
      this.analyser.smoothingTimeConstant = 0.8;

      this.source = this.audioCtx.createMediaStreamSource(mediaStream);
      this.source.connect(this.analyser);

      const bufferLength = this.analyser.frequencyBinCount;
      this.dataArray = new Uint8Array(bufferLength);

      this.isActive = true;
      this.draw();
    } catch (err) {
      console.warn('AudioVisualizer initialization warning:', err);
    }
  }

  stop() {
    this.isActive = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.clear();
  }

  clear() {
    if (!this.ctx || !this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.ctx.clearRect(0, 0, rect.width, rect.height);
  }

  draw() {
    if (!this.isActive || !this.ctx || !this.canvas) return;

    this.animationId = requestAnimationFrame(() => this.draw());

    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    this.ctx.clearRect(0, 0, width, height);

    if (!this.analyser) {
      // Idle gentle sine wave
      this.drawIdleWave(width, height);
      return;
    }

    this.analyser.getByteFrequencyData(this.dataArray);

    const barCount = 32;
    const barWidth = (width / barCount) - 3;
    let x = 0;

    for (let i = 0; i < barCount; i++) {
      const value = this.dataArray[i % this.dataArray.length] || 0;
      const percent = value / 255;
      const barHeight = Math.max(4, percent * (height - 10));
      const y = (height - barHeight) / 2;

      // Neon Gradient
      const gradient = this.ctx.createLinearGradient(0, y, 0, y + barHeight);
      gradient.addColorStop(0, '#00f2fe');
      gradient.addColorStop(0.5, '#4facfe');
      gradient.addColorStop(1, '#8b5cf6');

      this.ctx.fillStyle = gradient;
      this.ctx.shadowBlur = 8;
      this.ctx.shadowColor = 'rgba(0, 242, 254, 0.4)';

      this.drawRoundedRect(this.ctx, x, y, barWidth, barHeight, 3);
      x += barWidth + 3;
    }
  }

  drawIdleWave(width, height) {
    const time = Date.now() * 0.003;
    const centerY = height / 2;

    this.ctx.beginPath();
    this.ctx.strokeStyle = 'rgba(0, 242, 254, 0.2)';
    this.ctx.lineWidth = 2;

    for (let x = 0; x < width; x += 5) {
      const y = centerY + Math.sin(x * 0.04 + time) * 4;
      if (x === 0) {
        this.ctx.moveTo(x, y);
      } else {
        this.ctx.lineTo(x, y);
      }
    }
    this.ctx.stroke();
  }

  drawRoundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
  }
}

window.AudioVisualizer = AudioVisualizer;
