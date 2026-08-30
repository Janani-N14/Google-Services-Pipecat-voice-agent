"""
Automated Pipeline Integration Test.
Verifies that all pipeline components (STT, LLM, TTS, Context, RTVI) assemble without errors.
"""

import sys
from pathlib import Path
import aiohttp
import asyncio

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

from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor

from config import settings
from src.services.groq_service import create_groq_stt_service, create_groq_llm_service
from src.services.sarvam_service import create_sarvam_tts_service


async def test_full_pipeline_assembly():
    print("\n--- Testing Full Pipecat Pipeline Assembly ---", flush=True)
    async with aiohttp.ClientSession() as session:
        # 1. STT
        stt = create_groq_stt_service()
        print("  [PASS] STT service instantiated", flush=True)

        # 2. LLM with tools
        llm = create_groq_llm_service(register_tools=True)
        print("  [PASS] LLM service (Qwen 3.8-27B) instantiated with tools", flush=True)

        # 3. TTS
        tts = create_sarvam_tts_service(aiohttp_session=session, use_streaming=False)
        print("  [PASS] Sarvam TTS service instantiated", flush=True)

        # 4. Context & RTVI
        messages = [{"role": "system", "content": "You are a voice assistant."}]
        context = LLMContext(messages)
        context_aggregator = LLMContextAggregatorPair(context)
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        print("  [PASS] Context aggregator & RTVI initialized", flush=True)

        # 5. Pipeline Assembly
        pipeline = Pipeline(
            [
                rtvi,
                stt,
                context_aggregator.user(),
                llm,
                tts,
                context_aggregator.assistant(),
            ]
        )
        print("  [PASS] Pipecat Pipeline successfully created with all processors!", flush=True)
        return True


def main():
    ok = asyncio.run(test_full_pipeline_assembly())
    if ok:
        print("\n[SUCCESS] PIPELINE INTEGRATION TEST PASSED!\n", flush=True)
        return 0
    else:
        print("\n[FAIL] PIPELINE INTEGRATION TEST FAILED.\n", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
