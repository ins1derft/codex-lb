## 1. Compact Timeout Resilience

- [x] 1.1 Add a dedicated `compact_response_timeout_seconds` setting with a longer default
- [x] 1.2 Update compact upstream client timeout construction to use the new setting instead of hard-coded 60s values

## 2. Tests

- [x] 2.1 Add unit regression test for compact timeout propagation into upstream `POST`
- [x] 2.2 Add unit regression test for parsing `CODEX_LB_COMPACT_RESPONSE_TIMEOUT_SECONDS`

## 3. Spec Delta

- [x] 3.1 Add `responses-api-compat` delta for long-running compact requests
- [ ] 3.2 Run `openspec validate --specs` (`openspec` CLI is unavailable in this environment)
