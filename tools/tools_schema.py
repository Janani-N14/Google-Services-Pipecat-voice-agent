# tools/tools_schema.py
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema


send_email_schema = FunctionSchema(
    name="send_email",
    description="Send an email using Gmail OAuth",
    properties={
        "to": {
            "type": "string",
            "description": "Recipient email address"
        },
        "subject": {"type": "string", "description": "Email subject"},
        "body": {"type": "string", "description": "Email body content"},
    },
    required=["to", "subject", "body"],
)

create_calendar_event_schema = FunctionSchema(
    name="create_calendar_event",
    description="Create a Google Calendar event",
    properties={
        "summary": {"type": "string", "description": "Event title"},
        "description": {"type": "string", "description": "Event description"},
        "start_datetime": {"type": "string", "description": "Start datetime ISO string"},
        "end_datetime": {"type": "string", "description": "End datetime ISO string"},
        "timezone": {"type": "string", "description": "Timezone, e.g., Asia/Kolkata"},
        "attendees": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of attendee emails",
        },
    },
    required=["summary", "description", "start_datetime", "end_datetime"],
)

tools_schema = ToolsSchema(
    standard_tools=[
        send_email_schema,
        create_calendar_event_schema,
    ]
)
