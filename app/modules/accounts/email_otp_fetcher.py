from __future__ import annotations

import imaplib
import re
import time
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import Message
from email.policy import default as default_email_policy
from email.utils import parseaddr, parsedate_to_datetime

_OPENAI_OTP_SENDER = "noreply@tm.openai.com"
_OTP_CODE_PATTERN = re.compile(r"\b(\d{6})\b")


class EmailOtpFetchError(Exception):
    pass


class EmailOtpCodeNotFoundError(EmailOtpFetchError):
    pass


def default_imap_host_for_email(email_address: str) -> str:
    if "@" not in email_address:
        raise EmailOtpFetchError("Mailbox email must contain '@' for IMAP host resolution.")
    domain = email_address.split("@", maxsplit=1)[1].strip().lower()
    if not domain:
        raise EmailOtpFetchError("Mailbox email domain is empty.")
    return f"imap.{domain}"


def extract_chatgpt_code_from_message(message: Message) -> str | None:
    subject = _decode_header_value(message.get("Subject"))
    subject_match = _OTP_CODE_PATTERN.search(subject)
    if subject_match:
        return subject_match.group(1)

    body_text = _extract_message_text(message)
    body_match = _OTP_CODE_PATTERN.search(body_text)
    if body_match:
        return body_match.group(1)
    return None


class ImapEmailOtpFetcher:
    def __init__(
        self,
        *,
        sender: str = _OPENAI_OTP_SENDER,
        imap_port: int = 993,
        poll_interval_seconds: float = 2.0,
        max_messages: int = 40,
    ) -> None:
        self._sender = sender.lower()
        self._imap_port = imap_port
        self._poll_interval_seconds = max(poll_interval_seconds, 0.5)
        self._max_messages = max_messages

    def fetch_otp_code(
        self,
        *,
        mailbox_email: str,
        mailbox_password: str,
        timeout_seconds: float,
        since: datetime | None = None,
    ) -> str:
        if not mailbox_password:
            raise EmailOtpFetchError("Mailbox password is required for IMAP OTP retrieval.")
        host = default_imap_host_for_email(mailbox_email)
        timeout_seconds = max(timeout_seconds, 1.0)
        deadline = time.monotonic() + timeout_seconds
        since_utc = (since or datetime.now(timezone.utc) - timedelta(minutes=10)).astimezone(timezone.utc)

        try:
            with imaplib.IMAP4_SSL(host, self._imap_port) as client:
                client.login(mailbox_email, mailbox_password)
                status, _ = client.select("INBOX", readonly=True)
                if status != "OK":
                    raise EmailOtpFetchError("Unable to open INBOX for OTP retrieval.")

                while True:
                    code = self._try_find_code(client=client, since=since_utc)
                    if code:
                        return code
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(self._poll_interval_seconds, remaining))
        except EmailOtpFetchError:
            raise
        except imaplib.IMAP4.error as exc:
            raise EmailOtpFetchError(f"IMAP authentication failed: {exc}") from exc
        except Exception as exc:
            raise EmailOtpFetchError(f"IMAP OTP retrieval failed: {exc}") from exc

        raise EmailOtpCodeNotFoundError(
            f"OTP email from {self._sender} was not found within {int(timeout_seconds)} seconds.",
        )

    def _try_find_code(self, *, client: imaplib.IMAP4_SSL, since: datetime) -> str | None:
        status, data = client.search(None, "ALL")
        if status != "OK" or not data:
            return None

        raw_ids = data[0].split()
        if not raw_ids:
            return None

        for message_id in reversed(raw_ids[-self._max_messages :]):
            status, payload = client.fetch(message_id, "(RFC822)")
            if status != "OK" or not payload:
                continue
            raw_message = payload[0][1] if isinstance(payload[0], tuple) else None
            if not isinstance(raw_message, bytes):
                continue
            message = message_from_bytes(raw_message, policy=default_email_policy)
            sender = parseaddr(message.get("From", ""))[1].lower()
            if self._sender and self._sender not in sender:
                continue
            message_date = _parse_message_date(message.get("Date"))
            if message_date and message_date < since:
                continue
            code = extract_chatgpt_code_from_message(message)
            if code:
                return code
        return None


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_message_text(message: Message) -> str:
    if message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            if content_type != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                parts.append(_decode_bytes(payload, charset=part.get_content_charset()))
        return "\n".join(parts)

    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        return _decode_bytes(payload, charset=message.get_content_charset())
    if isinstance(payload, str):
        return payload
    return ""


def _decode_bytes(payload: bytes, *, charset: str | None) -> str:
    encoding = (charset or "utf-8").strip() or "utf-8"
    try:
        return payload.decode(encoding, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _parse_message_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
