"""
Tool schemas for Groq LLM tool-calling in Pipecat.
Defines parameters for Gmail sending and Google Calendar event creation.
"""

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

# Schema for Gmail send email
send_email_schema = FunctionSchema(
    name="send_email",
    description=(
        "Send an email message via the user's connected Gmail account. "
        "Requires the recipient email address, a subject line, and the message body."
    ),
    properties={
        "to": {
            "type": "string",
            "description": "The destination email address (e.g. user@example.com)",
        },
        "subject": {
            "type": "string",
            "description": "The subject line of the email",
        },
        "body": {
            "type": "string",
            "description": "The plain text body content of the email",
        },
    },
    required=["to", "subject", "body"],
)

# Schema for Google Calendar event creation
create_calendar_event_schema = FunctionSchema(
    name="create_calendar_event",
    description=(
        "Create an event on the user's primary Google Calendar. "
        "Requires event title, description, start time, and end time in ISO 8601 format."
    ),
    properties={
        "summary": {
            "type": "string",
            "description": "The title or summary of the calendar event",
        },
        "description": {
            "type": "string",
            "description": "Detailed description or notes for the calendar event",
        },
        "start_datetime": {
            "type": "string",
            "description": "Start datetime in ISO 8601 string format (e.g. 2026-03-01T10:00:00+05:30)",
        },
        "end_datetime": {
            "type": "string",
            "description": "End datetime in ISO 8601 string format (e.g. 2026-03-01T11:00:00+05:30)",
        },
        "timezone": {
            "type": "string",
            "description": "Timezone string, e.g. Asia/Kolkata or UTC. Default is Asia/Kolkata.",
        },
        "attendees": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of attendee email addresses to invite",
        },
    },
    required=["summary", "description", "start_datetime", "end_datetime"],
)

# Aggregated tools schema
tools_schema = ToolsSchema(
    standard_tools=[
        send_email_schema,
        create_calendar_event_schema,
    ]
)
