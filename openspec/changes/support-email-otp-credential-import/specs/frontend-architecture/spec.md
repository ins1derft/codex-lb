## MODIFIED Requirements

### Requirement: Accounts page

The Accounts page SHALL display a two-column layout: left panel with searchable account list, import button, and add account button; right panel with selected account details including usage, token info, and actions (pause/resume/delete/re-authenticate).

#### Scenario: Account import (credentials text)

- **WHEN** a user opens import dialog credentials mode
- **THEN** the UI documents support for both formats:
- `login:password:2fa_secret`
- `login:password:email:email_password`
- **AND** on submit it calls `POST /api/accounts/import-credentials`
