"""
Gmail MCP server — exposes send_email as a tool Claude Code can call directly.

Run via: python src/gmail_mcp_server.py
Registered in .claude/settings.json so Claude Code auto-starts it.
"""

import base64
import os
from email.mime.text import MIMEText

from mcp.server.fastmcp import FastMCP

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

mcp = FastMCP("gmail")


def _get_service():
    """Authenticate with Gmail and return an API service object."""
    token_path = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
    creds_path = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Gmail credentials file not found: {creds_path}\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials "
                    "and save it as credentials.json, or set GMAIL_CREDENTIALS_FILE."
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as fh:
            fh.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send a plain-text email via Gmail.

    Args:
        to: Recipient email address.
        subject: Subject line.
        body: Plain-text message body.

    Returns:
        Confirmation string with the Gmail message ID.
    """
    service = _get_service()

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    return f"Email sent to {to}. Gmail message ID: {result['id']}"


if __name__ == "__main__":
    mcp.run()
