from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from piper import PiperVoice
import uvicorn

app = FastAPI()

VOICE = PiperVoice.load(
    model_path=r"C:\Users\njana\piper\models\en_US-lessac-high.onnx"
)

SAMPLE_RATE = VOICE.config.sample_rate
print(f"Piper sample rate: {SAMPLE_RATE}")  # Check this value!

class TTSRequest(BaseModel):
    text: str

@app.post("/")
@app.post("/api/tts")
def tts(req: TTSRequest):
    audio_bytes = b""
    for chunk in VOICE.synthesize(req.text):
        audio_bytes += chunk.audio_int16_bytes
    
    # Return raw PCM, not WAV
    return Response(content=audio_bytes, media_type="audio/raw")

if __name__ == "__main__":
    uvicorn.run("piper_server:app", host="127.0.0.1", port=5002, log_level="info")