from __future__ import annotations

from email.message import EmailMessage

import pytest

from app.modules.accounts.email_otp_fetcher import (
    default_imap_host_for_email,
    extract_chatgpt_code_from_message,
)

pytestmark = pytest.mark.unit


def test_default_imap_host_for_email_uses_domain():
    assert default_imap_host_for_email("user@gmx.com") == "imap.gmx.com"


def test_extract_chatgpt_code_from_message_prefers_subject():
    message = EmailMessage()
    message["Subject"] = "Your ChatGPT code is 585082"
    message["From"] = "noreply@tm.openai.com"
    message.set_content("fallback 123456")

    assert extract_chatgpt_code_from_message(message) == "585082"


def test_extract_chatgpt_code_from_message_uses_body_when_subject_has_no_code():
    message = EmailMessage()
    message["Subject"] = "ChatGPT Log-in Code"
    message["From"] = "noreply@tm.openai.com"
    message.set_content("Please enter this code: 674492")

    assert extract_chatgpt_code_from_message(message) == "674492"


def test_extract_chatgpt_code_from_message_returns_none_without_six_digit_code():
    message = EmailMessage()
    message["Subject"] = "ChatGPT Log-in Code"
    message["From"] = "noreply@tm.openai.com"
    message.set_content("No code here")

    assert extract_chatgpt_code_from_message(message) is None
