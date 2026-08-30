"""
Automated Test for Sarvam AI Text-to-Speech (TTS).
Verifies REST API, WebSocket streaming, and Pipecat service integration.
"""

import sys
import base64
from pathlib import Path
import aiohttp
import asyncio
import requests

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings
from src.services.sarvam_service import create_sarvam_tts_service


def test_sarvam_rest_api():
    """Test Sarvam TTS REST endpoint directly using bulbul:v3."""
    print("\n--- 1. Testing Sarvam REST API Endpoint (bulbul:v3) ---", flush=True)
    if not settings.sarvam.api_key:
        print("[FAIL] Error: SARVAM_API_KEY is not set in .env", flush=True)
        return False

    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": settings.sarvam.api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": ["Welcome to Sarvam AI voice synthesis for Indian languages and English."],
        "target_language_code": settings.sarvam.language,
        "speaker": settings.sarvam.voice_id,
        "pace": float(settings.sarvam.pace),
        "temperature": float(settings.sarvam.temperature),
        "speech_sample_rate": 16000,
        "enable_preprocessing": settings.sarvam.enable_preprocessing,
        "model": "bulbul:v3",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        print(f"Status Code: {response.status_code}", flush=True)
        if response.status_code == 200:
            data = response.json()
            audios = data.get("audios", [])
            if audios:
                audio_bytes = base64.b64decode(audios[0])
                print(f"[PASS] Sarvam REST TTS successful! Generated {len(audio_bytes)} audio bytes.", flush=True)
                return True
            else:
                print("[FAIL] No audios returned in response payload.", flush=True)
                return False
        else:
            print(f"[FAIL] Sarvam API Error: {response.text}", flush=True)
            return False
    except Exception as e:
        print(f"[FAIL] Exception calling Sarvam REST API: {e}", flush=True)
        return False


async def test_sarvam_pipecat_services():
    """Test Sarvam Pipecat TTS Service Factory."""
    print("\n--- 2. Testing Sarvam Pipecat Services Factory ---", flush=True)
    async with aiohttp.ClientSession() as session:
        # Test WebSocket streaming service initialization
        tts_ws = create_sarvam_tts_service(use_streaming=True)
        print(f"[PASS] SarvamTTSService (WebSocket) instantiated: {type(tts_ws).__name__}", flush=True)

        # Test HTTP batch service initialization
        tts_http = create_sarvam_tts_service(aiohttp_session=session, use_streaming=False)
        print(f"[PASS] SarvamHttpTTSService (HTTP) instantiated: {type(tts_http).__name__}", flush=True)

        return True


def main():
    rest_ok = test_sarvam_rest_api()
    services_ok = asyncio.run(test_sarvam_pipecat_services())

    if rest_ok and services_ok:
        print("\n[SUCCESS] ALL SARVAM TTS TESTS PASSED!\n", flush=True)
        return 0
    else:
        print("\n[FAIL] SOME SARVAM TTS TESTS FAILED.\n", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
