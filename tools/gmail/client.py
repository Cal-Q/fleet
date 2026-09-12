"""Gmail API Client Module for Master Agent."""

import base64
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

CRED_DIR = Path(os.path.expanduser("~/.config/gmail"))
CREDENTIALS_FILE = CRED_DIR / "credentials.json"
TOKEN_FILE = CRED_DIR / "token.json"


def get_gmail_service() -> Resource:
    """Authenticate and return the Gmail API resource."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"Token file not found at {TOKEN_FILE}. Run auth.py first.")

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
        TOKEN_FILE.chmod(0o600)

    return build("gmail", "v1", credentials=creds)


def get_profile() -> Dict[str, Any]:
    """Fetch user Gmail profile."""
    service = get_gmail_service()
    return service.users().getProfile(userId="me").execute()


def list_messages(query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
    """List message summaries matching query."""
    service = get_gmail_service()
    res = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()
    messages = res.get("messages", [])

    summaries = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        summaries.append({
            "id": m["id"],
            "threadId": m.get("threadId"),
            "snippet": msg.get("snippet", ""),
            "from": headers.get("From", "Unknown"),
            "subject": headers.get("Subject", "(No Subject)"),
            "date": headers.get("Date", "")
        })
    return summaries


def _extract_body(part: Dict[str, Any]) -> str:
    """Recursively find and decode text/plain body from MIME parts."""
    if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
        return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    if "parts" in part:
        for p in part["parts"]:
            res = _extract_body(p)
            if res:
                return res
    if "body" in part and "data" in part["body"]:
        return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    return ""


def get_message(msg_id: str) -> Dict[str, Any]:
    """Fetch full message payload and decode body snippet."""
    service = get_gmail_service()
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
    body_text = _extract_body(payload)

    return {
        "id": msg_id,
        "from": headers.get("From", "Unknown"),
        "to": headers.get("To", "Unknown"),
        "subject": headers.get("Subject", "(No Subject)"),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body_text or msg.get("snippet", "")
    }


def send_message(to: str, subject: str, body: str, cc: Optional[str] = None) -> Dict[str, Any]:
    """Compose and send an email."""
    service = get_gmail_service()
    message = EmailMessage()
    message.set_content(body)
    message["To"] = to
    message["Subject"] = subject
    if cc:
        message["Cc"] = cc

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}
    return service.users().messages().send(userId="me", body=create_message).execute()
