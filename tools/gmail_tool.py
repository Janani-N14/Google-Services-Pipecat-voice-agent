# tools/gmail_tool.py
import base64
import os
from email.mime.text import MIMEText
from typing import Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pipecat.services.llm_service import FunctionCallParams  # <-- add this

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events"
]


def _get_gmail_service():
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

    return build("gmail", "v1", credentials=creds)


def send_email_tool(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send an email using Gmail API (OAuth).
    """
    service = _get_gmail_service()
    
    # Validate and clean email address
    to = to.strip()
    if not to or "@" not in to:
        raise ValueError(f"Invalid email address: {to}")
    
    message = MIMEText(body, "plain")
    message["to"] = to
    message["subject"] = subject
    message["from"] = "me"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    result = service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()

    return {
        "status": "sent",
        "message_id": result.get("id"),
        "to": to,
        "subject": subject,
    }


# NEW: Pipecat function-call handler that uses FunctionCallParams
async def send_email_handler(params: FunctionCallParams):
    args = params.arguments
    to_param = args.get("to", [])
    subject = args.get("subject", "")
    body = args.get("body", "")
    
    # Handle both string and array for 'to' parameter
    if isinstance(to_param, str):
        to = to_param if to_param else "njanani14062006@gmail.com"
    elif isinstance(to_param, list):
        to = to_param[0] if to_param else "njanani14062006@gmail.com"
    else:
        to = "njanani14062006@gmail.com"

    result = send_email_tool(to=to, subject=subject, body=body)

    # Return result to the LLM
    await params.result_callback(result)