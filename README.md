
# Pipecat Voice Assistant

**Real-Time Voice AI with Ollama + Sarvam + Google Tools**

A real-time conversational voice assistant built using:

* Pipecat – Realtime conversational pipeline framework
* Ollama (Kimi-K2.5) – LLM with tool calling
* Sarvam AI – Speech-to-Text & Text-to-Speech
* Google APIs – Gmail + Calendar (OAuth)
* WebRTC Transport – Low-latency streaming audio

---

# Features

* Real-time Speech-to-Text (Sarvam Saarika v2.5)
* Natural Text-to-Speech (Sarvam Bulbul v3)
* Tool-calling LLM (Ollama Kimi-k2.5)
* Create Google Calendar events
* Send emails via Gmail API
* Built-in usage metrics tracking
* Graceful conversation termination tool
* VAD + Smart Turn Detection

---

# Architecture Overview

```
User (WebRTC Mic)
        ↓
Transport Input
        ↓
VAD + Turn Detection
        ↓
Sarvam STT
        ↓
LLM Context Aggregator
        ↓
Ollama LLM (Tool Calling)
        ↓
Sarvam TTS
        ↓
Transport Output (Audio)
```

---

# Project Structure

```
.
├── main.py
├── tools/
│   ├── tools_schema.py
│   ├── gmail_tool.py
│   ├── calendar_tool.py
│   └── end_call.py
├── credentials.json
├── token.json
├── .env
└── README.md
```

---

# Installation

```bash
# 1. Clone repo
git clone <your-repo-url>
cd your-project

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

# Environment Variables

Create `.env` file:

```env
SARVAM_API_KEY=your_sarvam_api_key_here
```

---

# Ollama Setup

Install Ollama:

```bash
ollama pull kimi-k2.5:cloud
```

Ensure Ollama is running:

```bash
ollama serve
```

Default base URL used:

```
http://localhost:11434/v1
```

---

# Gmail + Calendar Setup (OAuth)

## 1. Create Google Cloud Project

Go to:
[https://console.cloud.google.com/](https://console.cloud.google.com/)

Enable:

* Gmail API
* Google Calendar API

## 2. Create OAuth Credentials

Download:

```
credentials.json
```

Place it in project root.

## 3. First Run Authorization

On first email/calendar use:

* Browser will open
* Grant permissions
* `token.json` will be generated

---

# Available Tools

## send_email

Send email using Gmail OAuth.

### Parameters

```json
{
  "to": "example@email.com",
  "subject": "Subject here",
  "body": "Email body"
}
```

---

## create_calendar_event

Create Google Calendar event.

### Parameters

```json
{
  "summary": "Meeting",
  "description": "Project discussion",
  "start_datetime": "2026-02-18T10:00:00+05:30",
  "end_datetime": "2026-02-18T10:30:00+05:30",
  "timezone": "Asia/Kolkata",
  "attendees": ["person@email.com"]
}
```

---

## end_conversation

Triggers:

* Speaks farewell message
* Gracefully shuts down pipeline

---

# Running the Bot

```bash
python bot_upd.py
```

You should see:

```
Starting Pipecat bot...
Sarvam STT initialized
Sarvam TTS initialized
Ollama LLM initialized
```

Then connect via WebRTC client.

---

# Metrics Tracking

After client disconnect:

```
CALL SUMMARY
Duration: 45.3s
Prompt Tokens: 124
Completion Tokens: 89
Total Tokens: 213
TTS Characters: 1430
```
---
