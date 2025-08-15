# Hobheap Server

FastAPI + SQLAlchemy async backend for knowledge & card/document management with tagging, versioning, OTP + JWT auth, rate limiting, and Alembic migrations. Managed with **[uv](https://docs.astral.sh/uv/)**.

## Contents

1. Quick Start
2. Project Overview & Architecture
3. Configuration (Environment Variables)
4. Database & Migrations (Alembic)
5. Running / Dev Workflow
6. Auth (JWT + OTP) & Rate Limiting
7. Data Model Summary
8. Core Endpoints (quick reference)
9. Tag Assignment & Filtering
10. Testing
11. Common Tasks (uv cheatsheet)
12. Roadmap / Next Steps
13. Troubleshooting

---

## 1. Quick Start

```bash
# clone repo then in the server/ directory
uv venv .venv          # optional: local virtualenv
uv sync                # install deps (runtime + dev)

# Run API (auto-reload if using fastapi[standard] watcher)
uv run fastapi dev src/app/main.py  # or:
# uv run python -m uvicorn app.main:app --reload

# Run tests
uv run pytest -q
```

Visit: <http://127.0.0.1:8000/docs> for interactive OpenAPI.

---

## 2. Project Overview & Architecture

| Layer | Location | Notes |
|-------|----------|-------|
| API Routers | `src/app/api/v1/` | FastAPI endpoints grouped by resource (users, cards, documents, tags). |
| Models | `src/app/models/entities.py` | SQLAlchemy 2.0 style async models (cards, versions, documents, tags, OTP). |
| Schemas | `src/app/schemas/base.py` | Pydantic v2 request/response models. |
| Services | `src/app/services/` | Auth (JWT), rate limiting. |
| Repositories | `src/app/repositories/` | Encapsulate persistence logic (tags, OTP). |
| DB Core | `src/app/core/db.py` | Async engine + session dependency. |
| Config | `src/app/core/config.py` | Central settings (DB URL normalization, rate limits, secrets). |
| Migrations | `alembic/` | Environment + versioned migration scripts. |
| Tests | `tests/` | Async tests (httpx + ASGITransport). |

Patterns:

* Soft delete via `is_deleted` + filtered queries.
* Card versioning increments on content change.
* Tag many-to-many via `card_tags` association.
* OTP short-lived codes + rate-limited issuance & verification.
* In-memory rate limiter (swap for Redis later).

---

## 3. Configuration (Environment Variables)

Define (optionally) in a `.env` or shell environment:

| Variable | Description | Default (if any) |
|----------|-------------|------------------|
| `DATABASE_URL` | Postgres or SQLite URL. | `sqlite+aiosqlite:///./dev.db` |
| `JWT_SECRET` | HMAC secret for JWT signing. | Hard-coded dev fallback (replace in prod) |
| `RATE_LIMIT_AUTH_ATTEMPTS` | Attempts per window for login/OTP. | 3 |
| `RATE_LIMIT_WINDOW_SECONDS` | Window size. | 300 |

`config.py` coerces bare `sqlite:///` forms to async driver if needed.

---

## 4. Database & Migrations (Alembic)

Initial schema + subsequent OTP migration exist (e.g., `20240814_0001_init.py`, `20240814_0002_add_otp.py`).

Common commands:

```bash
# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "describe change"

# Apply latest migrations
uv run alembic upgrade head

# Downgrade one step
uv run alembic downgrade -1

# View current revision
uv run alembic current
```

During early development you may reset:

```bash
rm dev.db  # or manually drop DB schema for Postgres
uv run alembic upgrade head
```

Autogenerate tips:

* Ensure new models are imported somewhere Alembic’s env loads them (they are via `models.entities`).
* Review generated diffs; add indices/constraints explicitly.

---

## 5. Running / Dev Workflow

```bash
uv run fastapi dev src/app/main.py   # auto-reload

# or explicit uvicorn
uv run python -m uvicorn app.main:app --reload --port 8000
```

Lifespan is used instead of deprecated startup events.

---

## 6. Auth (JWT + OTP) & Rate Limiting

Auth Flow (simplified, dev-oriented):

1. Create user (`POST /api/v1/users/`) returns basic user record.
2. Login (`POST /api/v1/users/login?email=...`) issues JWT if user exists.
3. OTP request (`POST /api/v1/users/otp/request?email=...`) issues one-time code (delivery stubbed).
4. OTP verify (`POST /api/v1/users/otp/verify?email=...&code=...`) would (future) mint session/JWT.

Rate Limiting:

* In-memory store keyed by action + identifier.
* Configured attempts/window in `config.py`.
* Endpoints raise HTTP 429 on exceed.
* Replace with Redis-backed implementation for multi-instance deployments.

Security NOTE: Replace dev JWT secret + add proper password or WebAuthn flows for production.

---

## 7. Data Model Summary

| Model | Purpose | Key Fields |
|-------|---------|-----------|
| User | Account identity | email, phone (optional) |
| Card | Content unit | content_md, template_type, soft delete |
| CardVersion | Historical snapshot | version_number, content_md |
| Document | Container for layout of cards | title, grid sizing |
| DocumentCard | Placement of a card in document | row, col, spans |
| Tag | Label for grouping/filtering | name, is_ai_generated |
| CardTag | Association (M2M) | card_id, tag_id |
| OTP | One-time passcode | code, expires_at, consumed |

---

## 8. Core Endpoints (Quick Reference)

Base path: `/api/v1`

| Resource | Method | Path | Notes |
|----------|--------|------|-------|
| Users | POST | `/users/` | create user |
| Users | POST | `/users/login` | login by email (JWT) |
| OTP | POST | `/users/otp/request` | issue OTP |
| OTP | POST | `/users/otp/verify` | verify OTP |
| Cards | POST | `/cards/` | create card (content_md) |
| Cards | GET | `/cards/` | list (filter: `tag`, `template_type`, pagination later) |
| Cards | GET | `/cards/{id}` | retrieve |
| Cards | DELETE | `/cards/{id}` | soft delete |
| Documents | POST | `/documents/` | create document |
| Documents | POST | `/documents/{id}/cards` | add card to doc grid |
| Documents | GET | `/documents/` | list (filter by tag) |
| Tags | POST | `/tags/` | create tag |
| Tags | GET | `/tags/` | list tags |
| Tags | POST | `/tags/assign` | assign tags to card (new) |
| Tags | GET | `/tags/cards/{card_id}/versions` | list versions of a card |

---

## 9. Tag Assignment & Filtering

Assign tags to a card (creates tag if absent):

```bash
curl -X POST \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/tags/assign \
  -d '{"card_id": 1, "tags": ["research", "draft"]}'
```

Response shape (`TagAssignOut`):

```json
{
  "card_id": 1,
  "tags": [ {"id": 5, "name": "research", "is_ai_generated": false}, ... ]
}
```

Filtering:

* Cards: `GET /api/v1/cards/?tag=research&template_type=plain`
* Documents: `GET /api/v1/documents/?tag=research`

Implementation detail: To avoid async lazy-load issues, the assignment endpoint inserts association rows manually (see `assign_tags` in `tags.py`).

---

## 10. Testing

Framework: `pytest` + `httpx` ASGITransport (pure in-process, no network) + `pytest-anyio`.

Run:

```bash
uv run pytest -q
```

Structure:

* `tests/conftest.py` creates/drops schema per session using metadata (NOT migrations). For migration verification you can spin a separate DB and run Alembic.
* `test_api_basic.py` – core CRUD & soft delete.
* `test_rate_limit.py` – rate limiting for login + OTP.
* `test_tags.py` – tag assignment + filtering.

---

```bash
uv run ruff check --fix
```


Add a new test file under `tests/` with `@pytest.mark.anyio` for async flows.

---

## 11. Common Tasks (uv Cheatsheet)

```bash
# Add runtime dep
uv add rich

# Add dev dep
uv add -D pytest

# Update lock / sync
uv sync

# Run a module
uv run python -m app.main
```

---

## 12. Roadmap / Next Steps

* Replace in-memory rate limiter with Redis (multi-instance safety).
* Persist successful OTP -> session or passwordless login issuing JWT.
* Add refresh tokens / revocation list.
* Expand filtering (multi-tag AND/OR logic, date ranges, search).
* Add indexes for frequent query patterns (composite on `card_tags(card_id, tag_id)`, tag lookups done; review others).
* Background tasks for stale OTP cleanup via scheduler.
* Export & archival endpoints.
* Observability: structured logging & metrics.

---

## 13. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `sqlalchemy.exc.MissingGreenlet` | Lazy load inside async context | Rewrite query to explicit `select`, avoid accessing unloaded relationships, or manual association insert (as done in tag assignment). |
| 429 Too Many Requests | Rate limit exceeded | Wait for window or adjust env vars. |
| JWT always same | Using static dev secret | Set `JWT_SECRET` in environment for rotation. |
| Migration not picking model | Model not imported | Ensure import path in Alembic env loads new model module. |

Reset local DB quickly (SQLite):

```bash
rm dev.db
uv run alembic upgrade head
```

---

## License / Notes

Internal development artifact; add license text if distributing.

---

Happy hacking!


