## MODIFIED Requirements

### Requirement: Credentials Batch Import API

The dashboard SHALL support two credential line formats in `POST /api/accounts/import-credentials`:
- `login:password:2fa_secret`
- `login:password:email:email_password`

#### Scenario: Mixed credential formats in one payload

- **WHEN** request body includes valid lines in either supported format
- **THEN** the API processes each line according to its format
- **AND** returns aggregated `total`, `imported`, `failed`, and per-line `results`

### Requirement: Per-account execution isolation

Automated authorization errors for one credential line SHALL NOT abort the entire batch execution.

#### Scenario: Email OTP line fails while others succeed

- **WHEN** one `login:password:email:email_password` line fails (mailbox auth/OTP issues)
- **THEN** other credential lines continue processing
- **AND** the failed line is returned with `status=failed` and non-empty `error`

## ADDED Requirements

### Requirement: Email OTP Authorization Path

When password verification transitions to email OTP verification, the system SHALL complete authorization by fetching the OTP from mailbox via IMAP and calling the upstream email OTP validation endpoint.

#### Scenario: Password verify returns email OTP page

- **WHEN** upstream `password/verify` response indicates `email_otp_verification`
- **THEN** system polls mailbox via IMAP using provided `email` and `email_password`
- **AND** extracts OTP from OpenAI email sender (`noreply@tm.openai.com`)
- **AND** validates OTP through `/api/accounts/email-otp/validate`
- **AND** continues OAuth flow to token exchange
