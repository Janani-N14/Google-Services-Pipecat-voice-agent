"""
Unified FastAPI Web Server for Pipecat Voice Agent.
Serves the futuristic glassmorphism frontend and handles WebRTC signaling + REST fallback endpoints.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

# Ensure UTF-8 console output on Windows
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

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from config import settings
from src.tools.schema import tools_schema
from src.tools.gmail_tool import send_email_tool
from src.tools.calendar_tool import create_calendar_event_tool

# Pipecat WebRTC Transport & Runner
from pipecat.runner.types import SmallWebRTCRunnerArguments
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequestHandler,
    IceCandidate,
)
import bot as bot_module

# Initialize SmallWebRTC Request Handler
small_webrtc_handler = SmallWebRTCRequestHandler(host="0.0.0.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to cleanly close WebRTC connections on shutdown."""
    logger.info("🚀 Pipecat Voice Agent Web Server started")
    yield
    logger.info("🛑 Shutting down Web Server and cleaning WebRTC connections...")
    await small_webrtc_handler.close()


app = FastAPI(
    title="Pipecat Voice Agent API",
    description="Real-time WebRTC voice agent with Groq Qwen 3.8-27B tool calling & Sarvam TTS",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for cloud deployment and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# WebRTC Signaling Routes (Pipecat SmallWebRTC)
# ==============================================================================

@app.post("/api/offer")
async def webrtc_offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    """Handle WebRTC SDP offer exchange."""
    async def webrtc_connection_callback(connection):
        runner_args = SmallWebRTCRunnerArguments(
            webrtc_connection=connection,
            body=request.request_data,
        )
        background_tasks.add_task(bot_module.bot, runner_args)

    answer = await small_webrtc_handler.handle_web_request(
        request=request,
        webrtc_connection_callback=webrtc_connection_callback,
    )
    return answer


@app.patch("/api/offer")
async def webrtc_ice_candidate(request: SmallWebRTCPatchRequest):
    """Handle WebRTC ICE candidate patching."""
    await small_webrtc_handler.handle_patch_request(request)
    return {"status": "success"}


# ==============================================================================
# REST API Endpoints
# ==============================================================================

@app.get("/api/status")
async def get_system_status():
    """Returns active models, services, and system configuration."""
    return {
        "status": "online",
        "framework": "Pipecat 0.0.97",
        "services": {
            "stt": {
                "provider": "Groq Cloud",
                "model": settings.groq.stt_model,
                "language": settings.groq.language,
            },
            "llm": {
                "provider": "Groq Cloud",
                "model": settings.groq.llm_model,
                "tool_calling": True,
            },
            "tts": {
                "provider": "Sarvam AI",
                "model": settings.sarvam.model,
                "voice_id": settings.sarvam.voice_id,
                "language": settings.sarvam.language,
                "streaming": settings.sarvam.use_streaming,
            },
        },
        "tools": ["send_email", "create_calendar_event"],
    }


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def text_chat_fallback(req: ChatRequest):
    """Fallback text chat directly with Groq Qwen 3.8-27B with tool calling."""
    if not settings.groq.api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq.api_key}",
        "Content-Type": "application/json",
    }

    tools_payload = [
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Send an email message via Gmail",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Subject"},
                        "body": {"type": "string", "description": "Body content"},
                    },
                    "required": ["to", "subject", "body"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_calendar_event",
                "description": "Create an event on Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Event title"},
                        "description": {"type": "string", "description": "Event description"},
                        "start_datetime": {"type": "string", "description": "ISO start datetime"},
                        "end_datetime": {"type": "string", "description": "ISO end datetime"},
                    },
                    "required": ["summary", "description", "start_datetime", "end_datetime"],
                },
            },
        },
    ]

    payload = {
        "model": settings.groq.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI voice assistant. If the user asks to send an email or schedule an event, invoke the appropriate tool.",
            },
            {"role": "user", "content": req.message},
        ],
        "tools": tools_payload,
        "tool_choice": "auto",
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code != 200:
            return JSONResponse(status_code=500, content={"error": res.text})

        data = res.json()
        choice = data["choices"][0]["message"]
        return {
            "response": choice.get("content") or "Processing request...",
            "tool_calls": choice.get("tool_calls", []),
        }
    except Exception as e:
        logger.error(f"Error in text chat fallback: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ==============================================================================
# Frontend Static Files Mount
# ==============================================================================

FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        """Serve frontend index.html at root."""
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_static_fallback(path: str):
        """Fallback to index.html for single-page app routing."""
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipecat Voice Agent Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=7860, help="Port number (default: 7860)")
    args = parser.parse_args()

    print(f"\n🚀 Voice Agent UI ready at: http://localhost:{args.port}/\n", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
