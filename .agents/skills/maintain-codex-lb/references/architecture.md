# codex-lb Architecture Reference

## Table of Contents

- System Overview
- Backend Runtime and Composition
- Backend Module Boundaries
- Core Infrastructure and Cross-Cutting Logic
- Persistence and Migrations
- API Surface and Contract Rules
- Frontend Architecture
- Testing Matrix and TDD Execution
- Change Recipes
- Non-Negotiable Conventions

## System Overview

codex-lb is a two-part web application:

- Backend: FastAPI + SQLAlchemy Async + SQLite/PostgreSQL support.
- Frontend: React 19 + Vite + TypeScript + Tailwind + TanStack Query + Zod.

Primary goals:

- Proxy OpenAI-compatible traffic (`/v1/*`, `/backend-api/codex/*`) across pooled ChatGPT accounts.
- Provide dashboard APIs and UI for accounts, usage, request logs, auth, settings, API keys.
- Keep OpenAI wire compatibility behavior explicit and test-covered.

Main entry points:

- Backend app factory: `app/main.py`
- DI composition: `app/dependencies.py`
- DB/session lifecycle: `app/db/session.py`
- Frontend app root: `frontend/src/App.tsx`

## Backend Runtime and Composition

`app/main.py` builds the app and composes lifecycle pieces:

- Invalidates settings and rate-limit caches on startup.
- Initializes DB and shared HTTP client.
- Starts usage refresh and model refresh schedulers.
- Registers middleware and exception handlers.
- Includes routers from each module.
- Serves SPA static files with fallback while excluding API prefixes.

Router registration in `app/main.py` is the backend routing source of truth.

Dependency injection is centralized in `app/dependencies.py`:

- Each feature has a `*Context` dataclass.
- Each context constructs repository + service with request-scoped `AsyncSession`.
- Proxy and OAuth use background session factories where needed.

Never bypass these providers for request handling code.

## Backend Module Boundaries

Module layout convention (`app/modules/<feature>/`):

- `api.py`: route handlers only (HTTP parsing, dependency wiring, response mapping, error translation).
- `service.py`: business logic and orchestration.
- `repository.py`: SQLAlchemy data access only.
- `schemas.py`: Pydantic request/response contracts at API edges.

Current feature modules:

- `accounts`: import/list/pause/reactivate/delete and trends.
- `usage`: usage summaries/history/window responses.
- `dashboard`: overview composition for cards/charts/windows.
- `request_logs`: log listing, filtering, and options facets.
- `dashboard_auth`: password/TOTP/session flows.
- `settings`: dashboard settings CRUD and cache invalidation points.
- `api_keys`: key CRUD, model restrictions, reservation-based quota accounting.
- `proxy`: OpenAI-compatible endpoints, streaming/non-streaming handling, load balancing.
- `oauth`: account authorization callbacks and token flows.
- `health`: health endpoints.

Boundary rules:

- Keep query construction in repositories, not in API handlers.
- Keep schema mapping out of repositories; map in service layer.
- Use typed dataclasses/protocols for internal payloads when shape is known.
- Do not return `dict[str, object]` as internal contracts if explicit types are possible.

## Core Infrastructure and Cross-Cutting Logic

Core packages in `app/core`:

- `auth`: dashboard/proxy auth dependencies, token refresh, TOTP utilities.
- `openai`: request/response models and mapping/parsing for compatibility.
- `clients`: upstream HTTP/OAuth/usage/model interactions.
- `balancer`: account selection and upstream failure handling semantics.
- `usage`: pricing/quota/window helpers and scheduling utilities.
- `middleware`: request ID and compressed-body decompression.
- `handlers`: unified exception-to-envelope mapping.
- `config`: typed settings and cache.

Cross-cutting contract highlights:

- Error envelopes are format-specific:
  - Dashboard style for `/api/*` routes.
  - OpenAI style for `/v1/*` and `/backend-api/*`.
- `DashboardModel` (`app/modules/shared/schemas.py`) enforces camelCase JSON and ISO-8601 datetime serialization.
- Datetime values exposed by dashboard APIs should stay datetime-typed in schemas (serialized as ISO strings), not epoch numbers.

## Persistence and Migrations

ORM models are in `app/db/models.py`:

- `Account`, `UsageHistory`, `RequestLog`, `StickySession`, `DashboardSettings`
- `ApiKey`, `ApiKeyLimit`, `ApiKeyUsageReservation`, `ApiKeyUsageReservationItem`

DB sessions:

- Request session: `get_session()`
- Background session: `get_background_session()`

Migration system:

- Alembic is the runtime source of truth (`app/db/alembic/versions/*`).
- Startup migrations are run by `app/db/session.py -> init_db()`.
- Migration orchestration/legacy bootstrap/drift checks live in `app/db/migrate.py`.

When schema changes:

1. Update ORM model(s).
2. Add Alembic revision under `app/db/alembic/versions/`.
3. Add/update migration and model tests.
4. Preserve idempotent startup migration behavior.

## API Surface and Contract Rules

Key route groups:

- Dashboard/API routes: `/api/...`
- OpenAI-compatible routes: `/v1/...`, `/backend-api/codex/...`
- Codex usage identity route: `/api/codex/usage` (separate auth semantics)

Contract and compatibility governance:

- Normative requirements live in `openspec/specs/**/spec.md`.
- Active behavior changes must be represented in `openspec/changes/**`.
- Responses and Chat compatibility contracts are strict; avoid silent behavior changes.

When modifying payloads/fields:

- Update Pydantic schemas (backend) and Zod schemas (frontend) together.
- Update integration tests asserting public API behavior.
- Keep error codes and status mapping stable unless explicitly changed in OpenSpec.

## Frontend Architecture

Frontend root: `frontend/`

- Router/layout/auth gate: `frontend/src/App.tsx`
- Feature-first structure under `frontend/src/features/*`
- Shared UI in `frontend/src/components/*`
- API fetch wrapper: `frontend/src/lib/api-client.ts`
- Query client defaults: `frontend/src/lib/query-client.ts`

Feature module pattern:

- `api.ts`: typed network calls.
- `schemas.ts`: Zod schemas as runtime + type source of truth.
- `hooks/*`: TanStack Query hooks and feature state.
- `components/*`: presentational and container components.

Critical frontend contracts:

- Auth gating uses `/api/dashboard-auth/session`.
- 401 responses trigger unauthorized handler and auth-state update.
- Server responses are validated through Zod; schema mismatch is treated as error.

## Testing Matrix and TDD Execution

Backend tests:

- Unit: `tests/unit` (fast isolated logic).
- Integration: `tests/integration` (FastAPI + DB + dependencies).
- Shared fixtures: `tests/conftest.py`.

Frontend tests:

- Unit/component/schema tests colocated as `*.test.ts(x)`.
- Integration UI flows: `frontend/src/__integration__/*`.
- Test infra: Vitest + Testing Library + MSW (`frontend/src/test/*`).

Playwright:

- Visual/snapshot flow: `frontend/screenshots/capture.spec.ts`.
- Command: `cd frontend && bun run screenshots`.
- MCP Playwright should be used for interactive UI/UX and logical user-flow validation in agent-driven changes.

Default quality commands:

```bash
# backend
uv run ruff check .
uv run ty check
uv run pytest tests/unit
uv run pytest tests/integration

# frontend
cd frontend
bun run lint
bun run typecheck
bun run test
bun run test:coverage
```

TDD execution order:

1. Add/adjust failing test first.
2. Implement minimal code to pass.
3. Refactor for clarity and maintainability.
4. Re-run relevant suites.
5. Run broader regression gates before completion.

## Change Recipes

### Add or change a backend feature

1. Update OpenSpec first for behavior/contract changes.
2. Add failing unit/integration tests.
3. Implement within existing module boundaries:
   - Route changes in `api.py`.
   - Business logic in `service.py`.
   - Persistence in `repository.py`.
   - Contract updates in `schemas.py`.
4. Wire/adjust context provider in `app/dependencies.py` if needed.
5. Include router in `app/main.py` if introducing a new module.
6. Run tests and linters.

### Add or change a frontend feature

1. Add or update Zod schemas in feature `schemas.ts`.
2. Add failing test(s) for component/hook/flow.
3. Update `api.ts`, hooks, then components.
4. Ensure query keys + invalidation semantics are correct.
5. Validate flow with MCP Playwright.
6. Run lint/type/tests.

### Change cross-layer API contracts

1. Define OpenSpec delta.
2. Change backend schema + service mapping.
3. Update integration tests for API outputs/status/errors.
4. Update frontend Zod schemas and feature usage.
5. Add UI integration assertions for the changed contract.

## Non-Negotiable Conventions

Apply these conventions consistently:

- Keep code readable and intention-revealing.
- Favor small, single-purpose functions/classes.
- Avoid hidden side effects and implicit dependencies.
- Pass only the data each function actually needs.
- Prefer composition over duplicated logic.
- Fail fast on invalid critical configuration/state.
- Avoid speculative fallback keys/config names.
- Avoid redundant state fields when values can be derived.
- Avoid global mutable state; isolate I/O behind explicit dependencies.
- Keep constructors focused on initialization, not heavy logic.
- Isolate external systems behind clients/repositories and mock them in tests.
- Write tests for new behavior and bug fixes before implementation.
