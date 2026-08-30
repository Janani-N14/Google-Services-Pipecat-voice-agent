"""
Sarvam AI Text-to-Speech (TTS) Service Initializer.
Configures Sarvam AI TTS (bulbul:v3) with Indian accent and multi-language support.
"""

from typing import Optional, Union
import aiohttp
from loguru import logger
from pipecat.services.sarvam.tts import SarvamTTSService, SarvamHttpTTSService
from pipecat.transcriptions.language import Language

from config import settings


def get_sarvam_language_enum(lang_str: str) -> Language:
    """Map string language codes to Pipecat Language Enum."""
    clean = lang_str.lower().replace("_", "-")
    if "en" in clean:
        return Language.EN
    elif "hi" in clean:
        return Language.HI
    elif "bn" in clean:
        return Language.BN
    elif "gu" in clean:
        return Language.GU
    elif "kn" in clean:
        return Language.KN
    elif "ml" in clean:
        return Language.ML
    elif "mr" in clean:
        return Language.MR
    elif "or" in clean:
        return Language.OR
    elif "pa" in clean:
        return Language.PA
    elif "ta" in clean:
        return Language.TA
    elif "te" in clean:
        return Language.TE
    return Language.EN


def create_sarvam_tts_service(
    api_key: Optional[str] = None,
    aiohttp_session: Optional[aiohttp.ClientSession] = None,
    model: Optional[str] = None,
    voice_id: Optional[str] = None,
    language: Optional[str] = None,
    pace: Optional[float] = None,
    temperature: Optional[float] = None,
    pitch: Optional[float] = None,
    loudness: Optional[float] = None,
    enable_preprocessing: Optional[bool] = None,
    use_streaming: Optional[bool] = None,
) -> Union[SarvamTTSService, SarvamHttpTTSService]:
    """
    Creates and configures a Sarvam AI TTS Service (WebSocket streaming or HTTP batch).

    Args:
        api_key: Sarvam AI API subscription key.
        aiohttp_session: Optional aiohttp ClientSession (used when use_streaming is False).
        model: Sarvam TTS model ID (default: "bulbul:v3").
        voice_id: Speaker voice ID (e.g., "shubh", "priya", "rohan", "aditya", "neha").
        language: Target language code (e.g., "en-IN", "hi-IN").
        pace: Speed of speech (0.5 to 2.0).
        temperature: Expressiveness / temperature (0.0 to 1.0, for bulbul:v3).
        pitch: Voice pitch modifier.
        loudness: Volume multiplier.
        enable_preprocessing: Enable text normalization.
        use_streaming: Whether to use real-time WebSocket streaming (default: True).

    Returns:
        SarvamTTSService (WebSocket) or SarvamHttpTTSService (HTTP).
    """
    key = api_key or settings.sarvam.api_key
    tts_model = model or settings.sarvam.model
    voice = voice_id or settings.sarvam.voice_id
    lang_code = language or settings.sarvam.language
    tts_pace = pace if pace is not None else settings.sarvam.pace
    tts_temp = temperature if temperature is not None else settings.sarvam.temperature
    tts_pitch = pitch if pitch is not None else settings.sarvam.pitch
    tts_loudness = loudness if loudness is not None else settings.sarvam.loudness
    preprocessing = enable_preprocessing if enable_preprocessing is not None else settings.sarvam.enable_preprocessing
    streaming = use_streaming if use_streaming is not None else settings.sarvam.use_streaming

    if not key:
        raise ValueError("SARVAM_API_KEY is not set. Please provide it in .env")

    lang_enum = get_sarvam_language_enum(lang_code)

    if streaming:
        input_params = SarvamTTSService.InputParams(
            language=lang_enum,
            pace=tts_pace,
            temperature=tts_temp,
            enable_preprocessing=preprocessing,
        )

        tts = SarvamTTSService(
            api_key=key,
            model=tts_model,
            voice_id=voice,
            params=input_params,
        )
        logger.info(
            f"🔊 Initialized Sarvam WebSocket Streaming TTS (Model: '{tts_model}', Voice: '{voice}', Language: '{lang_code}')"
        )
        return tts
    else:
        if aiohttp_session is None:
            raise ValueError("aiohttp_session is required when use_streaming=False for SarvamHttpTTSService")

        input_params = SarvamHttpTTSService.InputParams(
            language=lang_enum,
            pace=tts_pace,
            temperature=tts_temp,
            enable_preprocessing=preprocessing,
        )

        tts = SarvamHttpTTSService(
            api_key=key,
            aiohttp_session=aiohttp_session,
            model=tts_model,
            voice_id=voice,
            params=input_params,
        )
        logger.info(
            f"🔊 Initialized Sarvam HTTP Batch TTS (Model: '{tts_model}', Voice: '{voice}', Language: '{lang_code}')"
        )
        return tts
