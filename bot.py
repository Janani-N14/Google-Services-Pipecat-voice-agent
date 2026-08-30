"""
Pipecat Real-Time WebRTC Voice Bot
Powered by Groq STT (Whisper Turbo), Groq LLM (Qwen 3.8-27B with Tool Calling), and Sarvam AI TTS.
"""

import sys
import os

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError in Pipecat emojis
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr.encoding != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
os.environ["PYTHONIOENCODING"] = "utf-8"

from pathlib import Path
import aiohttp
from loguru import logger

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Pipeline core
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import LLMRunFrame

# Turn detection + VAD
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

# Context + RTVI
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor

# Runner / transport
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams

# Internal modular services & configuration
from config import settings
from src.tools.schema import tools_schema
from src.services.groq_service import create_groq_stt_service, create_groq_llm_service
from src.services.sarvam_service import create_sarvam_tts_service

logger.info("✨ Starting Pipecat Voice Agent...")


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """
    Constructs and runs the voice agent pipeline.
    """
    logger.info("🚀 Building voice agent pipeline...")

    session = aiohttp.ClientSession()

    # 1. Initialize Groq Speech-to-Text (STT)
    stt = create_groq_stt_service()

    @stt.event_handler("on_transcription")
    async def on_transcription(stt_instance, transcription):
        logger.info(f"🎤 User Speech: '{transcription}'")

    # 2. Initialize Groq LLM with Qwen 3.8-27B & Tool Calling
    llm = create_groq_llm_service(register_tools=True)

    # 3. Initialize Sarvam AI Text-to-Speech (TTS)
    try:
        tts = create_sarvam_tts_service(
            aiohttp_session=session,
            use_streaming=settings.sarvam.use_streaming
        )
    except Exception as e:
        logger.warning(f"⚠️ Falling back to Sarvam HTTP TTS due to: {e}")
        tts = create_sarvam_tts_service(
            aiohttp_session=session,
            use_streaming=False
        )

    # 4. Define Conversation Context and System Prompt
    system_prompt = (
        "You are an intelligent, friendly, and versatile AI voice assistant. "
        "You can chat naturally, answer general questions, tell jokes, and assist in multiple languages (such as English, Tamil, Hindi, etc.).\n\n"
        "You have direct access to Google Workspace functions:\n"
        "1. Email tool ('send_email'): When the user wants to send an email, collect the recipient's email address, subject, and body. "
        "As soon as you have all three parameters, you MUST call the `send_email` tool immediately. "
        "Do NOT pretend or claim that you sent the email in text without executing the tool!\n"
        "2. Calendar tool ('create_calendar_event'): When the user wants to schedule an event, collect the title, start datetime, and end datetime. "
        "Then call the `create_calendar_event` tool immediately.\n\n"
        "Voice Guidelines:\n"
        "- Keep spoken responses concise (1-2 sentences), warm, and spoken-friendly.\n"
        "- Never output raw JSON or '<tool_call>' text tags into the voice conversation. Always invoke the function tool natively."
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Explicitly pass tools_schema to LLMContext so the universal aggregator passes tools to Groq
    context = LLMContext(messages, tools=tools_schema)
    context_aggregator = LLMContextAggregatorPair(context)
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # 5. Assemble Pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    # 6. Lifecycle Event Handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("🟢 Client connected to voice session")
        messages.append(
            {
                "role": "user",
                "content": "Please greet me warmly and ask how you can help me today.",
            }
        )
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("🔴 Client disconnected from voice session")
        await session.close()
        await task.cancel()

    # 7. Execute Runner
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """
    Entrypoint configured for WebRTC transport with Silero VAD and Smart Turn Analyzer.
    """
    transport_params = {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    confidence=0.7,
                    start_secs=0.2,
                    stop_secs=0.8,
                    min_volume=0.6,
                ),
            ),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    if len(sys.argv) > 1 and any(arg in sys.argv for arg in ["--help", "-h", "-d", "--daily", "--whatsapp", "--twilio"]):
        from pipecat.runner.run import main
        main()
    else:
        from server import main as server_main
        server_main()

