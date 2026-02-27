## Context
HAR flow confirms that some logins return `page.type=email_otp_verification` after `/api/accounts/password/verify`, followed by `/api/accounts/email-otp/validate` and then consent/workspace flow.

## Design
1. Parser accepts two credential line contracts:
   - `login:password:2fa_secret`
   - `login:password:email:email_password`
2. Accounts service routes parsed lines to the correct authorization mode:
   - TOTP mode -> existing MFA path.
   - Email OTP mode -> IMAP-based OTP retrieval path.
3. Credential automator adds email OTP branch:
   - Detect `email_otp_verification` page after password verification.
   - Poll IMAP inbox for OpenAI OTP email (`noreply@tm.openai.com`).
   - Submit code to `/api/accounts/email-otp/validate`.
4. Keep per-line isolation semantics for batch import.

## Error Semantics
- Format errors stay `400 invalid_credentials_format` with no execution.
- IMAP/auth/OTP failures remain per-line `status=failed` in successful batch response.

## Security
- Raw passwords, mailbox passwords, and OTP codes are not persisted.
- OTP retrieval uses IMAP over SSL (`IMAP4_SSL`) and reads only mailbox content needed to extract code.
