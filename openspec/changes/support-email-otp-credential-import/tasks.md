## 1. Spec
- [x] 1.1 Add delta spec for `accounts-auth-automation` credential format + email OTP mode
- [x] 1.2 Add delta spec for `frontend-architecture` import UX copy

## 2. Backend
- [x] 2.1 Extend credential parser for dual format support
- [x] 2.2 Add IMAP OTP fetcher adapter for mailbox polling + OTP extraction
- [x] 2.3 Extend credential automator with `email_otp_verification` flow
- [x] 2.4 Wire service-level routing for TOTP vs email OTP inputs

## 3. Frontend
- [x] 3.1 Update import dialog copy/placeholders for dual credential formats

## 4. Testing
- [x] 4.1 Update parser unit tests for both formats and invalid lines
- [x] 4.2 Add unit tests for OTP extraction / IMAP helper behavior
- [x] 4.3 Add integration test for `import-credentials` email OTP format plumbing
- [x] 4.4 Run targeted backend + frontend tests
