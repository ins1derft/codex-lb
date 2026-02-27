## Why
`/api/accounts/import-credentials` currently supports only `email:password:2fa_secret` and depends on TOTP verification. Some accounts complete login via email OTP challenge instead of TOTP and require mailbox access to retrieve the one-time code.

## What Changes
- Add support for credential lines in format `login:password:email:email_password`.
- Extend automated authorization to handle `email_otp_verification` flow using IMAP mailbox polling.
- Keep existing `login:password:2fa_secret` flow intact for TOTP-based accounts.
- Update Accounts import UX copy to document both supported formats.

## Impact
- Capability affected: `accounts-auth-automation`, `frontend-architecture`.
- No database schema changes.
- Security-sensitive inputs (account password, mailbox password, OTP code) remain transient and are not persisted.
