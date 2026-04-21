## Why

`/backend-api/codex/responses/compact` sometimes returns `502 Bad Gateway` with `Timeout on reading data from socket` while the upstream compact task is still processing. The current client path hard-codes a 60-second total/read timeout for compact requests, which is shorter than real-world completion time for large context compaction.

This produces user-visible failures even when the upstream would have returned successfully if we had kept the socket open longer.

## What Changes

- replace the hard-coded 60-second compact upstream timeout with a dedicated settings-backed timeout
- default the compact timeout to a longer operational value aligned with long-running upstream processing
- add regression tests for timeout propagation and settings parsing

## Capabilities

### Modified Capabilities

- `responses-api-compat`: `/v1/responses/compact` and `/backend-api/codex/responses/compact` must tolerate long-running upstream compaction within the configured timeout budget

## Impact

- **code**: `app/core/config/settings.py`, `app/core/clients/proxy.py`
- **tests**: `tests/unit/test_proxy_utils.py`
- **api contract**: no response schema changes; operational timeout behavior becomes configurable
