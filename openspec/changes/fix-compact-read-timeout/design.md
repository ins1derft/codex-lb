## Context

Streaming Responses requests already use separate connect and read/idle controls, but compact requests still use:

- `total=60`
- `sock_read=60`

This means compact requests fail locally even when the upstream is still legitimately working on the response.

## Goal / Non-Goal

**Goal**
- allow compact requests to wait longer than 60 seconds by default
- make the timeout configurable without changing API payloads or error envelopes
- lock the behavior with unit tests

**Non-Goal**
- changing upstream retry behavior
- changing load-balancer selection
- changing response schemas or status mapping for real upstream failures

## Decision

### 1) Add a dedicated compact response timeout setting

Introduce `compact_response_timeout_seconds` in application settings. This is the single source of truth for how long the proxy waits for a compact JSON response after the upstream connection is established.

Default: `300.0` seconds.

### 2) Remove the compact hard-coded total timeout

Build the compact client timeout with:

- `total=None`
- `sock_connect=settings.upstream_connect_timeout_seconds`
- `sock_read=settings.compact_response_timeout_seconds`

This keeps connect bounded while allowing a full read window for long-running compaction.

### 3) Add regression tests

- verify `compact_responses()` passes the configured timeout into the upstream `POST`
- verify the new settings field is parsed from environment variables

## Trade-offs

- Longer waits mean a hung upstream request remains open longer before failing. This is intentional because the current 60-second limit is too aggressive for valid compaction workloads.
- Using a dedicated setting avoids overloading `stream_idle_timeout_seconds`, whose semantics are stream-specific.
