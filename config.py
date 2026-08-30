"""
Central configuration module for the Pipecat Voice Agent.
Loads environment variables and provides structured settings for Groq and Sarvam services.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Base workspace directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from base directory
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


@dataclass
class GroqConfig:
    api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("GROQ_LLM_MODEL", "qwen/qwen3.8-27b"))
    stt_model: str = field(default_factory=lambda: os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo"))
    language: str = field(default_factory=lambda: os.getenv("GROQ_STT_LANGUAGE", "en"))


@dataclass
class SarvamConfig:
    api_key: str = field(default_factory=lambda: os.getenv("SARVAM_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"))
    voice_id: str = field(default_factory=lambda: os.getenv("SARVAM_TTS_VOICE", "shubh"))
    language: str = field(default_factory=lambda: os.getenv("SARVAM_TTS_LANGUAGE", "en-IN"))
    pace: float = field(default_factory=lambda: float(os.getenv("SARVAM_TTS_PACE", "1.0")))
    temperature: float = field(default_factory=lambda: float(os.getenv("SARVAM_TTS_TEMPERATURE", "0.6")))
    pitch: float = field(default_factory=lambda: float(os.getenv("SARVAM_TTS_PITCH", "0.0")))
    loudness: float = field(default_factory=lambda: float(os.getenv("SARVAM_TTS_LOUDNESS", "1.5")))
    enable_preprocessing: bool = field(default_factory=lambda: os.getenv("SARVAM_TTS_PREPROCESSING", "true").lower() in ("true", "1", "yes"))
    use_streaming: bool = field(default_factory=lambda: os.getenv("SARVAM_TTS_STREAMING", "true").lower() in ("true", "1", "yes"))


@dataclass
class GoogleAuthConfig:
    credentials_path: str = field(
        default_factory=lambda: os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            str(BASE_DIR / "credentials.json")
        )
    )
    token_path: str = field(
        default_factory=lambda: os.getenv(
            "GOOGLE_TOKEN_PATH",
            str(BASE_DIR / "token.json")
        )
    )


@dataclass
class Settings:
    groq: GroqConfig = field(default_factory=GroqConfig)
    sarvam: SarvamConfig = field(default_factory=SarvamConfig)
    google: GoogleAuthConfig = field(default_factory=GoogleAuthConfig)


# Global settings instance
settings = Settings()
