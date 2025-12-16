import os
import aiohttp
from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import LLMRunFrame

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIConfig
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)

from pipecat.services.whisper.stt import WhisperSTTService, Model
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.piper.tts import PiperTTSService

from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer

load_dotenv(override=True)
app = FastAPI()

async def build_pipeline(transport):
    session = aiohttp.ClientSession()

    stt = WhisperSTTService(model=Model.TINY,
                             device="auto"
    )

    llm = OLLamaLLMService(
        model="llama3.2:1b",
        base_url="http://localhost:11434/v1",
    )

    tts = PiperTTSService(
        base_url=os.getenv("PIPER_BASE_URL", "http://127.0.0.1:5002/api/tts"),
        aiohttp_session=session,
    )

    messages = [{"role": "system", "content": "You are a friendly AI assistant."}]
    context = LLMContext(messages)
    aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        RTVIProcessor(RTVIConfig(config=[])),
        stt,
        aggregator.user(),
        llm,
        tts,
        transport.output(),
        aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True),
    )

    messages.append({"role": "system", "content": "Say hello."})
    await task.queue_frames([LLMRunFrame()])

    return task, session

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    transport = FastAPIWebsocketTransport(
        websocket=ws,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=ProtobufFrameSerializer(),
        ),
    )

    task, session = await build_pipeline(transport)
    await task.run()

    await session.close()