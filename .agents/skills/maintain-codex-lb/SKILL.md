---
name: maintain-codex-lb
description: Maintain and extend codex-lb (FastAPI + SQLAlchemy + React/Vite) with repository-specific architecture guardrails. Use when implementing new features, fixing bugs, refactoring modules, changing API/data contracts, or adding tests in this repository. Enforce OpenSpec-first workflow, strict typing, SOLID/OOP boundaries, TDD (tests before code), and verification via pytest, Vitest, and MCP Playwright UI checks.
---

# Maintain codex-lb

Execute codex-lb changes without violating architecture, contracts, or style.

## Workflow

1. Scope the change and read specs first.
- Read relevant `openspec/specs/**/spec.md`.
- If behavior, schema, or contract changes are needed, create/update an OpenSpec change in `openspec/changes/**` before implementation.
- Keep code and OpenSpec artifacts synchronized.

2. Load focused project context.
- Read `references/architecture.md`.
- Pull only the sections needed for the changed area (backend module, frontend feature, migrations, testing).

3. Apply mandatory TDD loop.
- Write or update failing tests first.
- Implement the smallest change to make tests pass.
- Refactor while keeping tests green.

4. Respect codex-lb architecture boundaries.
- Backend modules follow `api.py` (routes), `service.py` (business logic), `repository.py` (DB), `schemas.py` (I/O).
- Construct request-scoped contexts in `app/dependencies.py`; repositories must use request-scoped `AsyncSession`.
- Keep strict typing with dataclasses/Pydantic when payload shapes are known; avoid generic dict/object contracts.
- Preserve existing error envelope contracts (`dashboard` vs `openai`) and route auth dependencies.
- Frontend features follow `api.ts`, `schemas.ts` (Zod SSOT), hooks, and components with TanStack Query.

5. Validate thoroughly before finishing.
- Run lint/type/tests for touched backend and frontend areas.
- Run integration tests for changed API contracts.
- Use MCP Playwright to validate key UI/UX and logical user flows.
- Add targeted regression tests for timing/concurrency/flaky-risk paths.

6. Report explicit change impact.
- Call out changed contracts (fields/types/status/events).
- Reference updated tests and OpenSpec files.

## Testing Requirements

Treat these as required, not optional:

- Backend unit tests in `tests/unit` for pure logic and service/repository behavior with fakes.
- Backend integration tests in `tests/integration` for route + DB + dependency behavior.
- Frontend unit/integration tests under `frontend/src` (`*.test.ts(x)` and `__integration__`).
- UI/UX and end-to-end logical checks through MCP Playwright sessions.
- Regression tests for unstable edge cases (retries, locks, stream termination, race-sensitive flows).

## Default Verification Commands

```bash
# Backend quality gates
uv run ruff check .
uv run ty check
uv run pytest tests/unit
uv run pytest tests/integration

# Frontend quality gates
cd frontend
bun run lint
bun run typecheck
bun run test
bun run test:coverage
```

Run targeted subsets during iteration (`pytest -k ...`, single frontend test files), then rerun relevant full suites before completion.

## UI and E2E Validation

- Validate critical user journeys with MCP Playwright (login, dashboard data visibility, accounts actions, settings/API keys flows).
- For visual regressions or docs screenshots, use `cd frontend && bun run screenshots`.
- Prefer asserting visible behavior and API outcomes over implementation details.

## References

- Architecture and module map: `references/architecture.md`
