"""
Google Calendar integration tool for scheduling events via Google Workspace API.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from pipecat.services.llm_service import FunctionCallParams
from src.utils.auth import get_calendar_service


def create_calendar_event_tool(
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "Asia/Kolkata",
    attendees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Creates a new Google Calendar event on the user's primary calendar.

    Args:
        summary: Title/Summary of the event.
        description: Description of the event.
        start_datetime: ISO 8601 string (e.g. 2026-03-01T10:00:00+05:30).
        end_datetime: ISO 8601 string (e.g. 2026-03-01T11:00:00+05:30).
        timezone: Timezone identifier (default: "Asia/Kolkata").
        attendees: Optional list of email addresses.

    Returns:
        Dict with status, event ID, HTML link, and summary.
    """
    if not summary:
        return {"status": "error", "error": "Event summary/title is required."}
    if not start_datetime or not end_datetime:
        return {"status": "error", "error": "Both start_datetime and end_datetime are required."}

    try:
        service = get_calendar_service()
        if not service:
            return {"status": "error", "error": "Google Calendar service credentials unavailable."}

        event_body = {
            "summary": summary,
            "description": description or "",
            "start": {
                "dateTime": start_datetime,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": timezone,
            },
            "attendees": [{"email": e.strip()} for e in (attendees or []) if e and "@" in e],
        }

        created_event = (
            service.events()
            .insert(calendarId="primary", body=event_body, sendUpdates="all")
            .execute()
        )

        logger.info(
            f"✅ Calendar event '{summary}' created successfully. (ID: {created_event.get('id')})"
        )
        return {
            "status": "success",
            "message": f"Calendar event '{summary}' successfully created.",
            "event_id": created_event.get("id"),
            "htmlLink": created_event.get("htmlLink"),
            "summary": summary,
            "start": start_datetime,
            "end": end_datetime,
        }
    except Exception as e:
        logger.error(f"❌ Failed to create Google Calendar event: {e}")
        return {
            "status": "error",
            "error": f"Failed to create calendar event: {str(e)}",
            "summary": summary,
        }


async def create_calendar_event_handler(params: FunctionCallParams):
    """
    Pipecat tool call handler invoked by LLM when `create_calendar_event` function is called.
    """
    args = params.arguments
    logger.info(f"🗓️ Invoking create_calendar_event handler with args: {args}")

    # Handle alternate parameter naming variations from various LLM generations
    summary = args.get("summary") or args.get("event_title") or args.get("title", "")
    description = args.get("description", "")
    start_datetime = args.get("start_datetime") or args.get("start_time") or args.get("start", "")
    end_datetime = args.get("end_datetime") or args.get("end_time") or args.get("end", "")
    timezone = args.get("timezone") or "Asia/Kolkata"
    attendees = args.get("attendees", [])

    if isinstance(attendees, str):
        attendees = [attendees]

    result = create_calendar_event_tool(
        summary=summary,
        description=description,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        timezone=timezone,
        attendees=attendees,
    )

    # Return structured result back to the LLM context
    await params.result_callback(result)
