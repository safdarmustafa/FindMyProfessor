from __future__ import annotations

"""
Gmail API client — MIME construction and message sending.

SECURITY RULES:
- Never log email body, CV contents, or access tokens.
- Never expose CV file paths to the browser.
- The From address must be the connected Gmail account; it is set server-side.
"""

import base64
import logging
import mimetypes
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


class GmailSendResult:
    def __init__(self, message_id: str, thread_id: str | None) -> None:
        self.message_id = message_id
        self.thread_id = thread_id


class GmailApiError(Exception):
    """Raised when the Gmail API returns a non-retriable error."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or "gmail_error"


def build_mime_message(
    *,
    from_addr: str | None,
    to_addr: str,
    subject: str,
    body: str,
    attachment_bytes: bytes,
    attachment_display_name: str,
) -> dict[str, str]:
    """
    Construct a MIME multipart email message ready for Gmail's messages.send API.

    Returns {'raw': <url-safe-base64-encoded bytes>}.

    from_addr is optional: when only gmail.send scope is granted, the account
    email is not available. Omitting From is safe — Gmail overwrites it with
    the authenticated account when userId='me' is used in messages.send.

    The attachment is passed in as raw bytes, already resolved server-side
    from whichever storage backend is active (local disk or Supabase
    Storage); this function never touches the filesystem or a storage path.
    attachment_display_name is the user-visible filename.
    """
    msg = MIMEMultipart()
    if from_addr:
        msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    mime_type, _ = mimetypes.guess_type(attachment_display_name)
    if not mime_type:
        mime_type = "application/octet-stream"
    main_type, sub_type = mime_type.split("/", 1)

    if main_type == "application":
        part = MIMEApplication(attachment_bytes, _subtype=sub_type)
    else:
        part = MIMEApplication(attachment_bytes, _subtype="octet-stream")

    part["Content-Disposition"] = f'attachment; filename="{attachment_display_name}"'
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return {"raw": raw}


def send_message(*, access_token: str, mime_message: dict[str, str]) -> GmailSendResult:
    """
    Call Gmail's messages.send endpoint.

    Returns GmailSendResult on success.
    Raises GmailApiError on failure.
    NEVER logs access_token or message body.
    """
    try:
        import googleapiclient.discovery
        import googleapiclient.errors
        from google.oauth2.credentials import Credentials

        creds = Credentials(token=access_token)
        service = googleapiclient.discovery.build(
            "gmail", "v1", credentials=creds, cache_discovery=False
        )
        response: dict[str, Any] = (
            service.users()
            .messages()
            .send(userId="me", body=mime_message)
            .execute()
        )
        message_id = response.get("id", "")
        thread_id = response.get("threadId")
        logger.info("Gmail message sent successfully (message_id redacted).")
        return GmailSendResult(message_id=message_id, thread_id=thread_id)

    except Exception as exc:
        # Extract a safe error code without logging sensitive details
        code = _extract_error_code(exc)
        raise GmailApiError(str(exc), code=code) from exc


def _extract_error_code(exc: Exception) -> str:
    try:
        # googleapiclient.errors.HttpError has .status_code
        status = getattr(exc, "status_code", None) or getattr(exc, "resp", {})
        if hasattr(status, "status"):
            return f"http_{status.status}"
        if isinstance(status, int):
            return f"http_{status}"
    except Exception:
        pass
    return "gmail_error"
