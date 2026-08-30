"""
Voice Agent Tools Package
Contains function schemas and handlers for Google Workspace tools (Gmail & Calendar).
"""

from src.tools.schema import tools_schema, send_email_schema, create_calendar_event_schema
from src.tools.gmail_tool import send_email_tool, send_email_handler
from src.tools.calendar_tool import create_calendar_event_tool, create_calendar_event_handler

__all__ = [
    "tools_schema",
    "send_email_schema",
    "create_calendar_event_schema",
    "send_email_tool",
    "send_email_handler",
    "create_calendar_event_tool",
    "create_calendar_event_handler",
]
