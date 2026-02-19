# tools/calendar_tool.py
import os
from typing import Dict, Any, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pipecat.services.llm_service import FunctionCallParams  # <-- add this

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.send"
]


def _get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_calendar_event_tool(
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "Asia/Kolkata",
    attendees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a Google Calendar event.
    Datetime format example: 2026-02-18T10:00:00+05:30
    """
    service = _get_calendar_service()

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_datetime,
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": timezone,
        },
        "attendees": [{"email": e} for e in (attendees or [])],
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all",
    ).execute()

    return {
        "status": "created",
        "event_id": created_event.get("id"),
        "htmlLink": created_event.get("htmlLink"),
        "summary": summary,
    }


# NEW: Pipecat function-call handler
async def create_calendar_event_handler(params: FunctionCallParams):
    """
    Pipecat handler for the `create_calendar_event` tool.

    Expects arguments (accepts multiple naming conventions):
      - summary/event_title (str)
      - description (str)
      - start_datetime/start_time (str)
      - end_datetime/end_time (str)
      - timezone (str, optional)
      - attendees (list[str], optional)
    """
    args = params.arguments

    # Handle alternate parameter names
    summary = args.get("summary") or args.get("event_title")
    description = args.get("description", "")
    start_datetime = args.get("start_datetime") or args.get("start_time")
    end_datetime = args.get("end_datetime") or args.get("end_time")
    timezone = args.get("timezone", "Asia/Kolkata")
    attendees = args.get("attendees")  # should be a list of emails

    result = create_calendar_event_tool(
        summary=summary,
        description=description,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        timezone=timezone,
        attendees=attendees,
    )

    # Return result back into the LLM context
    await params.result_callback(result)


# ============================================================
# Simple manual test entrypoint
# ============================================================

def main():
    print("🗓️ Testing Google Calendar event creation...")

    result = create_calendar_event_tool(
        summary="Test Event from Pipecat Tool",
        description="This is a test event created from calendar_tool.py",
        start_datetime="2026-02-18T10:00:00+05:30",
        end_datetime="2026-02-18T10:30:00+05:30",
        timezone="Asia/Kolkata",
        attendees=[],  # or ["someone@example.com"]
    )

    print("✅ Event created!")
    print("Result:")
    print(result)


if __name__ == "__main__":
    main()
