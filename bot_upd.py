import os
import time
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
from pipecat.frames.frames import LLMRunFrame, MetricsFrame, Frame

# ======================
# Metrics
# ======================
from pipecat.metrics.metrics import LLMUsageMetricsData, TTSUsageMetricsData
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

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
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService

# ======================
# Tools
# ======================
from tools.tools_schema import tools_schema
from tools.calendar_tool import create_calendar_event_handler

# ======================
# Environment
# ======================
load_dotenv(override=True)

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    raise ValueError("❌ SARVAM_API_KEY not found in environment")

logger.info("✅ All imports loaded successfully")


# ============================================================
# Metrics Logger
# ============================================================

class MetricsLogger(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tts_characters = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Ensure proper StartFrame handling
        await super().process_frame(frame, direction)

        if isinstance(frame, MetricsFrame):
            for d in frame.data:
                if isinstance(d, LLMUsageMetricsData):
                    tokens = d.value
                    self.total_prompt_tokens += tokens.prompt_tokens
                    self.total_completion_tokens += tokens.completion_tokens
                elif isinstance(d, TTSUsageMetricsData):
                    self.total_tts_characters += d.value

        await self.push_frame(frame, direction)

    def log_summary(self, duration_secs: float):
        logger.info("=" * 60)
        logger.info("📊 CALL SUMMARY")
        logger.info(f"⏱  Duration:             {duration_secs:.1f}s")
        logger.info(f"🔤 Prompt Tokens:        {self.total_prompt_tokens}")
        logger.info(f"💬 Completion Tokens:    {self.total_completion_tokens}")
        logger.info(
            f"📝 Total Tokens:         {self.total_prompt_tokens + self.total_completion_tokens}"
        )
        logger.info(f"🔊 TTS Characters:       {self.total_tts_characters}")
        logger.info("=" * 60)


# ============================================================
# Main Bot Logic
# ============================================================

async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("🚀 Starting bot pipeline")

    call_start_time = None
    metrics_logger = MetricsLogger()

    # -------------------------
    # STT
    # -------------------------
    stt = SarvamSTTService(
        api_key=SARVAM_API_KEY,
        model="saarika:v2.5",
    )

    @stt.event_handler("on_error")
    async def on_stt_error(processor, error):
        logger.error(f"🔥 Sarvam STT error: {error.error}, fatal={error.fatal}")

    logger.info("✅ Sarvam STT initialized")

    # -------------------------
    # TTS
    # -------------------------
    tts = SarvamTTSService(
        api_key=SARVAM_API_KEY,
        target_language_code="en-IN",
        model="bulbul:v3",
        speaker="shubh",
        pace=1.0,
        speech_sample_rate=24000,
    )

    logger.info("✅ Sarvam TTS initialized")

    # -------------------------
    # LLM
    # -------------------------
    llm = OLLamaLLMService(
        model="kimi-k2.5:cloud",
        base_url="http://localhost:11434/v1",
        tools_schema=tools_schema,
    )

    llm.register_function("create_calendar_event", create_calendar_event_handler)
    logger.info("✅ Ollama LLM initialized")

    # -------------------------
    # Context
    # -------------------------
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "Use provided tools when required. "
                "Always confirm successful actions."
            ),
        }
    ]

    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # -------------------------
    # Pipeline (Correct Order)
    # -------------------------
    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            llm,
            tts,
            metrics_logger,     
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

    @task.event_handler("on_pipeline_error")
    async def on_pipeline_error(task, frame):
        logger.error(f"🚨 Pipeline error: {frame.error}")

    # -------------------------
    # Transport Events
    # -------------------------
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        nonlocal call_start_time
        call_start_time = time.time()

        logger.info("🔗 Client connected")
        messages.append(
            {"role": "system", "content": "Greet the user politely."}
        )

        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("❌ Client disconnected")

        duration = time.time() - call_start_time if call_start_time else 0
        metrics_logger.log_summary(duration)

        # 🔥 Graceful shutdown order
        try:
            await stt.stop()
        except Exception:
            pass

        try:
            await tts.stop()
        except Exception:
            pass

        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


# ============================================================
# Entry Point
# ============================================================

async def bot(runner_args: RunnerArguments):
    transport_params = {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(stop_secs=0.2),
            ),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()