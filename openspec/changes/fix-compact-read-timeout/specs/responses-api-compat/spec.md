## ADDED Requirements

### Requirement: Compact requests honor a configurable upstream response timeout
The service MUST wait for upstream `/responses/compact` completion using a configurable timeout instead of a hard-coded 60-second limit. The timeout MUST be long enough by default to allow legitimate long-running compact operations and MUST remain separately configurable from stream idle timeout behavior.

#### Scenario: Compact completes after more than 60 seconds but within configured timeout
- **WHEN** the upstream compact task needs longer than 60 seconds and finishes within the configured compact timeout
- **THEN** the service keeps the upstream request open and returns the compact response instead of failing locally at 60 seconds

#### Scenario: Compact timeout is configured via environment
- **WHEN** `CODEX_LB_COMPACT_RESPONSE_TIMEOUT_SECONDS` is set
- **THEN** the compact upstream client uses that configured timeout budget for socket reads
