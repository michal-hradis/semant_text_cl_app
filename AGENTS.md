# AGENTS.md — Coding Agent Guidelines

This file documents conventions, workflows, and requirements for AI coding agents (and human developers) working in this repository.

---

## Project Overview

**semant_text_cl_app** is a human text-classification web application. Annotators log in, select up to 6 classification tasks, and label text passages one by one. The collected labels serve as ground truth for benchmarking AI text-classification methods.

- **Backend**: Python (FastAPI, SQLAlchemy async, fastapi-users, pydantic v2)  
- **Frontend**: Quasar v2 (Vue 3 Composition API, TypeScript, Pinia, Axios)  
- **Database**: SQLite (dev) / PostgreSQL (prod via `DATABASE_URL` env var)  
- **Auth**: JWT bearer tokens via fastapi-users  

---

## Repository Layout

```
backend/                Python FastAPI application
  text_classifier/      Main package (renamed from title_annotator)
    config.py           Settings from environment variables
    database.py         Async SQLAlchemy engine + User table
    db_model.py         ORM models
    crud.py             Database access functions
    routes.py           FastAPI routers
    main.py             App factory + middleware
    users.py            fastapi-users configuration
  tests/                pytest test suite
  run.py                Entry-point (uvicorn)
  requirements.txt      Python dependencies

frontend/               Quasar / Vue 3 SPA
  src/
    pages/              One .vue file per route
    components/         Reusable UI components
    services/api.ts     Axios API wrapper
    types/api.ts        TypeScript interfaces matching backend schemas
    stores/             Pinia stores
    router/routes.ts    Vue Router config

prompts/                Classification task definitions (Markdown, one file per task)
logs/                   Change summaries (see below)
example.jsonl           Sample text upload file
rebuild_task.md         Ongoing design notes and task breakdown
```

---

## Running the Application

### Backend
```bash
cd backend
pip install -r requirements.txt
python run.py          # starts on port 8002 by default
```

Key environment variables (all optional, sensible defaults in `config.py`):
| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///database.sqlite` | SQLAlchemy async URL |
| `PRODUCTION` | `false` | Disables CORS wildcard, enables stricter settings |
| `PORT` | `8002` | uvicorn listen port |
| `ALLOWED_ORIGIN` | `http://localhost:9000` | Frontend origin for CORS |
| `JWT_PRIVATE_KEY` | `supersecret` | **Must be changed in production** |
| `SECRET` | `XYZ123…` | fastapi-users secret — **must be changed in production** |
| `ADMIN` | (email) | Email of the initial superuser |
| `ADMIN_PASSWORD` | `admin123` | **Must be changed in production** |

### Frontend
```bash
cd frontend
npm install
npm run dev            # starts on http://localhost:9000 (Quasar default)
npm run build          # production build → dist/spa/
```

---

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/
```

- Tests live in `backend/tests/`.  
- All new backend features **must** include corresponding tests.  
- Use a temporary in-memory or file-based SQLite database for integration tests (see `tests_crud.py` for the pattern).  
- Frontend tests: currently none — add Vitest unit tests for complex store/service logic when introduced.

---

## Code Conventions

### Backend (Python)
- Python ≥ 3.11; use `from __future__ import annotations` where helpful.
- Async-first: all DB calls use `AsyncSession`; do not mix sync SQLAlchemy.
- Pydantic v2 models for all request/response schemas in `base_objects.py` (or a renamed equivalent).
- Raise `DBError` (defined in `database.py`) for database-layer failures; let FastAPI exception handlers convert to HTTP responses.
- Never store secrets in source files — always read from environment variables via `config.py`.
- Keep routes thin: business logic belongs in `crud.py` or dedicated service modules.

### Frontend (TypeScript / Vue)
- Vue 3 Composition API (`<script setup>`); no Options API.
- All API types must mirror backend Pydantic schemas in `src/types/api.ts`.
- API calls go through `src/services/api.ts` — do not call `axios` directly from components or stores.
- One Pinia store per domain (auth, tasks, annotations).
- Quasar components preferred over raw HTML for UI consistency.

### General
- No hard-coded credentials, URLs, or file paths — use env vars or config objects.
- Keep commits small and focused; one logical change per commit.

---

## Documentation

- Public-facing API changes must be reflected in `frontend/openapi.json` (regenerate with FastAPI's `/openapi.json` endpoint).
- Significant refactors or new features should update `rebuild_task.md` and/or add a file under `docs/` if needed.
- Each classification task description lives in `prompts/{task_id}.md` and follows the established format (see existing files).

---

## Change Log

**Every non-trivial change must be summarised in a dedicated log file:**

```
logs/{iso_datetime}_{task}.md
```

- `iso_datetime` — UTC timestamp in `YYYYMMDDTHHMMSS` format, e.g. `20260508T143000`.
- `task` — short snake_case description, e.g. `rename_package`, `add_annotation_api`, `leaderboard_page`.
- The log file should contain: what changed, why, and any decisions made.

Example path: `logs/20260508T143000_rename_package.md`

The `logs/` directory is committed to the repository.

---

## Security Checklist (OWASP Top 10 reminders)

- **A01 Broken Access Control**: All admin routes must check `user.is_superuser`. User-scoped routes must never expose other users' data.
- **A02 Cryptographic Failures**: `JWT_PRIVATE_KEY`, `SECRET`, and `ADMIN_PASSWORD` must be strong random values in production.
- **A03 Injection**: Use SQLAlchemy ORM or parameterised queries exclusively — never interpolate user input into SQL.
- **A05 Security Misconfiguration**: `PRODUCTION=true` must be set in production to disable CORS wildcard.
- **A07 Identification and Authentication Failures**: JWT lifetime is configurable; keep it short in production.

---

## Task Definition Format (JSON for DB import)

When parsing `.md` prompt files or creating new tasks, produce JSON in this canonical shape:

```json
{
  "id": "style",
  "name": "Style",
  "description_md": "# Task\nCharacterise the register/style…",
  "multi_choice": true,
  "max_choices": 2,
  "enabled": true,
  "classes": [
    {"id": "formal",       "label_en": "Formal",       "label_cs": "formální"},
    {"id": "neutral",      "label_en": "Neutral",      "label_cs": "neutrální"}
  ]
}
```

Admin uploads this JSON file via `POST /api/admin/tasks`.

---

## Text Upload Format (JSONL)

See `example.jsonl` for the full schema. Required fields the app extracts:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string (UUID) | Unique text identifier; duplicate uploads are upserted |
| `text` | string | The passage shown to annotators |
| `language` | string | ISO 639-3 code (e.g. `ces`, `eng`) |

All other fields are stored verbatim as a JSON blob for later export and comparison with AI-generated labels.

---

## Key Design Decisions (recorded here for reference)

| Decision | Choice | Reason |
|---|---|---|
| Task selection UX | User picks ≤ 6 tasks; texts served one-by-one | Keeps cognitive load manageable |
| Task definitions storage | DB (parsed from .md → JSON → uploaded) | Allows runtime admin control |
| Text storage | Full JSON blob + extracted fields | Preserves AI labels for benchmarking |
| Duplicate text upload | Upsert by `id` | Safe re-import of updated data |
| Registration | Open (no invite token) | Low friction for annotators |
| Backend package name | `text_classifier` (renamed from `title_annotator`) | Reflects new purpose |
| DB schema | `tasks`, `texts`, `annotations` tables | Clean break from old rating schema |
