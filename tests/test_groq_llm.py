"""
Automated Test for Groq STT and Groq LLM (Qwen 3.8-27B) Tool Calling.
Verifies function-calling schemas for Gmail sending and Google Calendar event creation.
"""

import sys
import json
from pathlib import Path
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
from src.services.groq_service import create_groq_stt_service, create_groq_llm_service


def test_groq_tool_calling():
    """Test tool calling with Groq Qwen 3.8-27B model directly via Groq API."""
    print("\n--- 1. Testing Groq Qwen 3.8-27B Tool Calling via API ---", flush=True)
    if not settings.groq.api_key:
        print("[FAIL] Error: GROQ_API_KEY is not set in .env", flush=True)
        return False

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq.api_key}",
        "Content-Type": "application/json",
    }

    tools = [
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
                        "body": {"type": "string", "description": "Body text"},
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
                        "summary": {"type": "string", "description": "Title"},
                        "description": {"type": "string", "description": "Notes"},
                        "start_datetime": {"type": "string", "description": "ISO start datetime"},
                        "end_datetime": {"type": "string", "description": "ISO end datetime"},
                    },
                    "required": ["summary", "description", "start_datetime", "end_datetime"],
                },
            },
        },
    ]

    # Test Case 1: Send Email
    payload_email = {
        "model": settings.groq.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful voice assistant. When asked to send an email, call the send_email tool.",
            },
            {
                "role": "user",
                "content": "Please send an email to sarah@example.com with the subject 'Weekly Sync' saying 'Meeting at 4pm.'",
            },
        ],
        "tools": tools,
        "tool_choice": "auto",
    }

    print(f"Testing model: {settings.groq.llm_model} for 'send_email'...", flush=True)
    res_email = requests.post(url, json=payload_email, headers=headers, timeout=15)
    if res_email.status_code != 200:
        print(f"[FAIL] Groq API Error: {res_email.text}", flush=True)
        return False

    msg_email = res_email.json()["choices"][0]["message"]
    tool_calls_email = msg_email.get("tool_calls", [])
    if not tool_calls_email:
        print(f"[FAIL] Failed: Model did not generate a tool call. Response: {msg_email}", flush=True)
        return False

    call_name = tool_calls_email[0]["function"]["name"]
    call_args = json.loads(tool_calls_email[0]["function"]["arguments"])
    print(f"[PASS] 'send_email' tool triggered successfully: name={call_name}, args={call_args}", flush=True)

    # Test Case 2: Create Calendar Event
    payload_cal = {
        "model": settings.groq.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful voice assistant. When asked to schedule an event, call create_calendar_event.",
            },
            {
                "role": "user",
                "content": "Schedule a Team Retrospective on March 2nd 2026 from 10:00 to 11:00 AM with description Sprint wrap-up.",
            },
        ],
        "tools": tools,
        "tool_choice": "auto",
    }

    print(f"Testing model: {settings.groq.llm_model} for 'create_calendar_event'...", flush=True)
    res_cal = requests.post(url, json=payload_cal, headers=headers, timeout=15)
    if res_cal.status_code != 200:
        print(f"[FAIL] Groq API Error: {res_cal.text}", flush=True)
        return False

    msg_cal = res_cal.json()["choices"][0]["message"]
    tool_calls_cal = msg_cal.get("tool_calls", [])
    if not tool_calls_cal:
        print(f"[FAIL] Failed: Model did not generate a tool call. Response: {msg_cal}", flush=True)
        return False

    cal_name = tool_calls_cal[0]["function"]["name"]
    cal_args = json.loads(tool_calls_cal[0]["function"]["arguments"])
    print(f"[PASS] 'create_calendar_event' tool triggered successfully: name={cal_name}, args={cal_args}", flush=True)

    return True


def test_pipecat_groq_services():
    """Test Pipecat GroqSTTService and GroqLLMService initialization."""
    print("\n--- 2. Testing Pipecat Groq Services Initializers ---", flush=True)
    stt = create_groq_stt_service()
    print(f"[PASS] GroqSTTService initialized: model={stt.model_name}", flush=True)

    llm = create_groq_llm_service(register_tools=True)
    print(f"[PASS] GroqLLMService initialized: model={llm.model_name}", flush=True)

    return True


def main():
    api_ok = test_groq_tool_calling()
    services_ok = test_pipecat_groq_services()

    if api_ok and services_ok:
        print("\n[SUCCESS] ALL GROQ LLM & STT TESTS PASSED!\n", flush=True)
        return 0
    else:
        print("\n[FAIL] SOME GROQ TESTS FAILED.\n", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
