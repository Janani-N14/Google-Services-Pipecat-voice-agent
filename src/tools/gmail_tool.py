"""
Gmail integration tool for sending emails via Google Workspace API.
"""

import base64
from email.mime.text import MIMEText
from typing import Dict, Any, Union, List
from loguru import logger
from pipecat.services.llm_service import FunctionCallParams
from src.utils.auth import get_gmail_service


def send_email_tool(to: Union[str, List[str]], subject: str, body: str) -> Dict[str, Any]:
    """
    Sends an email using the authorized Gmail API client.

    Args:
        to: Destination email address (str or list of str).
        subject: Email subject.
        body: Email message body in plain text.

    Returns:
        Dict with status, message ID, recipient, and subject.
    """
    # Clean and resolve recipient address
    if isinstance(to, list):
        recipient = to[0].strip() if to else ""
    elif isinstance(to, str):
        recipient = to.strip()
    else:
        recipient = str(to).strip()

    if not recipient or "@" not in recipient:
        error_msg = f"Invalid or missing recipient email address: '{recipient}'"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    try:
        service = get_gmail_service()
        if not service:
            return {"status": "error", "error": "Gmail service credentials unavailable."}

        message = MIMEText(body, "plain", "utf-8")
        message["to"] = recipient
        message["subject"] = subject
        message["from"] = "me"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

        logger.info(f"✅ Email successfully sent to '{recipient}' (Message ID: {result.get('id')})")
        return {
            "status": "success",
            "message": f"Email successfully sent to {recipient}",
            "message_id": result.get("id"),
            "to": recipient,
            "subject": subject,
        }
    except Exception as e:
        logger.error(f"❌ Failed to send email via Gmail API: {e}")
        return {
            "status": "error",
            "error": f"Failed to send email: {str(e)}",
            "to": recipient,
            "subject": subject,
        }


async def send_email_handler(params: FunctionCallParams):
    """
    Pipecat tool call handler invoked by LLM when `send_email` function is called.
    """
    args = params.arguments
    logger.info(f"📧 Invoking send_email handler with args: {args}")

    to_param = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")

    result = send_email_tool(to=to_param, subject=subject, body=body)

    # Return structured result back to the LLM context
    await params.result_callback(result)
