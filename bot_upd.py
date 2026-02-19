#
# Pipecat Local WebRTC Voice Bot (VAD + Smart Turn via user aggregator)
#

import os
import aiohttp

from dotenv import load_dotenv
from loguru import logger

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (first run may take ~20s)\n")

# ======================
# Turn detection + VAD
# ======================
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

# ======================
# Pipeline core
# ======================
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import LLMRunFrame

# ======================
# Context + RTVI
# ======================
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor

# ======================
# Runner / transport
# ======================
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams

# ======================
# Services
# ======================
# from pipecat.services.whisper.stt import WhisperSTTService, Model
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.piper.tts import PiperTTSService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.transcriptions.language import Language


from tools.tools_schema import tools_schema
from tools.gmail_tool import send_email_handler
from tools.calendar_tool import create_calendar_event_handler

# ======================
# Env
# ======================
load_dotenv(override=True)
logger.info("✅ All imports loaded successfully")


# ============================================================
# Main bot logic
# ============================================================

async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting bot pipeline")

    session = aiohttp.ClientSession()

    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3-turbo",
        language=Language.EN,
    )
    
    # Add event handler to log transcriptions
    @stt.event_handler("on_transcription")
    async def on_transcription(stt, transcription):
        logger.info(f"🎤 TRANSCRIPTION: '{transcription}'")
    
    logger.info(f"Groq STT initialized with model whisper-large-v3-turbo on language {Language.EN}")

    # ---------- TTS (Piper)
    tts = PiperTTSService(
        base_url="http://127.0.0.1:5002/api/tts",
        voice_id="en_US-lessac-high",
        aiohttp_session=session,
    )
    logger.info("Piper TTS initialized")

    # ---------- LLM (Ollama)
    llm = OLLamaLLMService(
        model="gpt-oss:20b-cloud",
        base_url="http://localhost:11434/v1",
        tools_schema=tools_schema,
    )

    # Register tool handlers
    llm.register_function("send_email", send_email_handler)
    llm.register_function("create_calendar_event", create_calendar_event_handler)

    logger.info("OLLama LLM initialized")

    # --- System Prompt ---
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "When sending emails, ask the user for: recipient email address, subject, and email body content. "
                "When creating calendar events, ask for: event title, description, start time, and end time. "
                "Only call the tools when you have all required information. "
                "After a tool runs successfully, confirm the action to the user."
            ),
        },
    ]

    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)
    logger.info("LLM context and aggregator initialized with system prompt")

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

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

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        messages.append(
            {"role": "system", "content": "Say hello and briefly introduce yourself."}
        )
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await session.close()
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


# ============================================================
# Entry point (WebRTC only)
# ============================================================

async def bot(runner_args: RunnerArguments):
    transport_params = {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                        params=VADParams(stop_secs=0.2), ),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main() 