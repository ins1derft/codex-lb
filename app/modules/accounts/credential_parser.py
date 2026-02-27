from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CredentialLine:
    line: int
    email: str
    account_password: str
    totp_secret: str | None = None
    otp_email: str | None = None
    otp_email_password: str | None = None


class InvalidCredentialFormatError(ValueError):
    pass


def parse_credential_lines(credentials_text: str) -> list[CredentialLine]:
    parsed: list[CredentialLine] = []
    for line_number, raw_line in enumerate(credentials_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        delimiter_count = line.count(":")
        if delimiter_count < 2:
            raise InvalidCredentialFormatError(
                f"Invalid credentials format at line {line_number}. "
                "Expected <login>:<password>:<2fa_secret> or <login>:<password>:<email>:<email_password>.",
            )

        first_delimiter = line.find(":")
        email = line[:first_delimiter].strip()
        if not email:
            raise InvalidCredentialFormatError(f"Login is required at line {line_number}.")

        last_delimiter = line.rfind(":")
        second_last_delimiter = line.rfind(":", 0, last_delimiter)
        if last_delimiter <= first_delimiter or last_delimiter >= len(line) - 1:
            raise InvalidCredentialFormatError(
                f"Invalid credentials format at line {line_number}. "
                "Expected <login>:<password>:<2fa_secret> or <login>:<password>:<email>:<email_password>.",
            )

        # If the segment before the last delimiter looks like an email, treat as
        # email-OTP mode; otherwise keep legacy TOTP parsing, allowing ':' in password.
        otp_email_candidate = (
            line[second_last_delimiter + 1 : last_delimiter].strip()
            if second_last_delimiter > first_delimiter
            else ""
        )
        if delimiter_count == 2 or "@" not in otp_email_candidate:
            account_password = line[first_delimiter + 1 : last_delimiter]
            totp_secret = line[last_delimiter + 1 :].strip()
            if not account_password:
                raise InvalidCredentialFormatError(f"Secret is required at line {line_number}.")
            if not totp_secret:
                raise InvalidCredentialFormatError(f"2FA secret is required at line {line_number}.")
            parsed.append(
                CredentialLine(
                    line=line_number,
                    email=email,
                    account_password=account_password,
                    totp_secret=totp_secret,
                ),
            )
            continue

        if second_last_delimiter <= first_delimiter:
            raise InvalidCredentialFormatError(
                f"Invalid credentials format at line {line_number}. "
                "Expected <login>:<password>:<email>:<email_password>.",
            )
        account_password = line[first_delimiter + 1 : second_last_delimiter]
        otp_email = otp_email_candidate
        otp_email_password = line[last_delimiter + 1 :].strip()
        if not account_password:
            raise InvalidCredentialFormatError(f"Secret is required at line {line_number}.")
        if not otp_email or "@" not in otp_email:
            raise InvalidCredentialFormatError(f"Mailbox email is required at line {line_number}.")
        if not otp_email_password:
            raise InvalidCredentialFormatError(f"Mailbox password is required at line {line_number}.")

        parsed.append(
            CredentialLine(
                line=line_number,
                email=email,
                account_password=account_password,
                totp_secret=None,
                otp_email=otp_email,
                otp_email_password=otp_email_password,
            ),
        )

    if not parsed:
        raise InvalidCredentialFormatError("No credentials provided.")

    return parsed
