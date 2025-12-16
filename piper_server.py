import io
import wave
import numpy as np
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from piper import PiperVoice
import uvicorn

app = FastAPI()

VOICE = PiperVoice.load(
    model_path=r"C:\Users\njana\piper\models\en_US-lessac-high.onnx"
)

SAMPLE_RATE = VOICE.config.sample_rate

class TTSRequest(BaseModel):
    text: str

@app.post("/api/tts")
def tts(req: TTSRequest):
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)      # int16
        wf.setframerate(SAMPLE_RATE)

        for chunk in VOICE.synthesize(req.text):
            # AudioChunk has audio_int16_bytes attribute with the audio data already in int16 format
            wf.writeframes(chunk.audio_int16_bytes)

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="audio/wav")

if __name__ == "__main__":
    uvicorn.run(
        "piper_server:app",
        host="0.0.0.0",
        port=5002,
        log_level="info",
    )
