"""
Groq AI Service Initializer for STT and LLM with Tool Calling.
Configures Groq Whisper Turbo for Speech-to-Text and Groq Qwen 3.8-27B for LLM orchestration.
"""

from typing import Optional
from loguru import logger
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transcriptions.language import Language

from config import settings
from src.tools.schema import tools_schema
from src.tools.gmail_tool import send_email_handler
from src.tools.calendar_tool import create_calendar_event_handler


def get_language_enum(lang_str: str) -> Language:
    """Map string language codes to Pipecat Language Enum."""
    lang_map = {
        "en": Language.EN,
        "en-in": Language.EN_IN,
        "hi": Language.HI,
        "es": Language.ES,
        "fr": Language.FR,
        "de": Language.DE,
    }
    return lang_map.get(lang_str.lower(), Language.EN)


def create_groq_stt_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
) -> GroqSTTService:
    """
    Creates and configures a GroqSTTService instance.

    Args:
        api_key: Groq API key (falls back to config/env).
        model: STT model ID (default: whisper-large-v3-turbo).
        language: Language code (default: en).

    Returns:
        Configured GroqSTTService.
    """
    key = api_key or settings.groq.api_key
    stt_model = model or settings.groq.stt_model
    lang_code = language or settings.groq.language

    if not key:
        raise ValueError("GROQ_API_KEY is not set. Please provide it in .env")

    lang_enum = get_language_enum(lang_code)

    stt = GroqSTTService(
        api_key=key,
        model=stt_model,
        language=lang_enum,
    )

    logger.info(f"🎤 Initialized Groq STT Service with model '{stt_model}' on language '{lang_enum.name}'")
    return stt


def create_groq_llm_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    register_tools: bool = True,
) -> GroqLLMService:
    """
    Creates and configures a GroqLLMService instance using Qwen 3.8-27B with tools.

    Args:
        api_key: Groq API key (falls back to config/env).
        model: LLM model ID (default: qwen/qwen3.8-27b).
        register_tools: Whether to attach tools schema and register Gmail/Calendar tool handlers.

    Returns:
        Configured GroqLLMService.
    """
    key = api_key or settings.groq.api_key
    llm_model = model or settings.groq.llm_model

    if not key:
        raise ValueError("GROQ_API_KEY is not set. Please provide it in .env")

    llm = GroqLLMService(
        api_key=key,
        model=llm_model,
        tools_schema=tools_schema if register_tools else None,
    )

    if register_tools:
        llm.register_function("send_email", send_email_handler)
        llm.register_function("create_calendar_event", create_calendar_event_handler)
        logger.info("🛠️ Registered tool handlers: 'send_email', 'create_calendar_event'")

    logger.info(f"🤖 Initialized Groq LLM Service with model '{llm_model}'")
    return llm
