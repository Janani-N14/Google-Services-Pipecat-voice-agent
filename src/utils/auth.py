"""
Unified Google OAuth2 credentials manager for Gmail and Calendar APIs.
"""

import os
from pathlib import Path
from typing import Optional
from loguru import logger
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]


def get_google_credentials() -> Optional[Credentials]:
    """
    Retrieves or generates valid Google OAuth2 credentials for Gmail and Calendar.
    Checks token.json first; if absent or expired, attempts browser OAuth flow using credentials.json.
    """
    token_path = Path(settings.google.token_path)
    creds_path = Path(settings.google.credentials_path)

    # Check fallback paths in current directory if configured paths don't exist
    if not token_path.exists() and Path("token.json").exists():
        token_path = Path("token.json")
    if not creds_path.exists() and Path("credentials.json").exists():
        creds_path = Path("credentials.json")

    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning(f"Error loading {token_path}: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired Google OAuth credentials...")
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}. Re-authenticating...")
                creds = None

        if not creds:
            if not creds_path.exists():
                logger.error(
                    f"Google credentials file not found at {creds_path}. "
                    f"Please place your OAuth client secrets JSON as 'credentials.json' "
                    f"or set GOOGLE_CREDENTIALS_PATH in .env"
                )
                raise FileNotFoundError(
                    f"Google credentials file not found: {creds_path}. "
                    f"Please download OAuth client credentials from Google Cloud Console."
                )

            logger.info(f"Starting Google OAuth interactive login using {creds_path}...")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)

        # Persist updated credentials
        try:
            with open(token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
            logger.info(f"Saved updated Google OAuth token to {token_path}")
        except Exception as e:
            logger.warning(f"Failed to save token to {token_path}: {e}")

    return creds


def get_gmail_service():
    """Build and return an authorized Gmail API service client."""
    creds = get_google_credentials()
    return build("gmail", "v1", credentials=creds)


def get_calendar_service():
    """Build and return an authorized Google Calendar API service client."""
    creds = get_google_credentials()
    return build("calendar", "v3", credentials=creds)
