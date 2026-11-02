# AGENTS.md — Coding Agent Guidelines

## Project Overview

**semant_text_cl_app** collects human text-classification annotations for benchmarking AI classifiers. Annotators log in, select up to 6 tasks, and label texts one by one.

**Start with [docs/README.md](docs/README.md)** (documentation index). Use the terms in [docs/glossary.md](docs/glossary.md) in code, docs and logs.

- **Backend**: Python (FastAPI, SQLAlchemy async, fastapi-users, Pydantic v2)
- **Frontend**: Quasar v2 (Vue 3 Composition API, TypeScript, Pinia, Axios)
- **Database**: SQLite (dev) / PostgreSQL (prod via `DATABASE_URL`)
- **Auth**: JWT bearer tokens via fastapi-users

---

## Repository Layout

```
backend/
  text_classifier/      Main package
    config.py           Settings from env vars
    database.py         Async SQLAlchemy engine + User table + DBError
    db_model.py         ORM models (Task, TextItem, Annotation, UserReliability)
    base_objects.py     Pydantic v2 request/response schemas
    crud.py             Database access functions
    routes.py           FastAPI routers (api_route, admin_route)
    main.py             App factory + middleware
    users.py            fastapi-users configuration
    prompt_parser.py    Markdown → task definition parser
    reservations.py     In-memory soft reservations for the sampler
    reliability.py      Annotator reliability job
  tests/                pytest test suite
  run.py                Entry-point (uvicorn)
  *.py                  Maintenance scripts (see docs/operations.md)
  requirements.txt

frontend/
  src/
    pages/              One .vue file per route
    components/         Reusable UI components
    services/api.ts     Axios API wrapper (all API calls go here)
    types/api.ts        TypeScript interfaces mirroring backend schemas
    stores/             Pinia stores (currently auth only)
    router/routes.ts    Vue Router config

prompts/                Prompt files: English task definitions (Markdown, one per task)
docs/                   Current-state documentation; docs/history/ = superseded plans
deploy/                 Dockerfiles, docker-compose
logs/                   Change summaries (see below)
example.jsonl           Sample text upload file
```

---

## Running

### Backend
```bash
cd backend
pip install -r requirements.txt
python run.py          # default: http://localhost:8003
```

Environment variables: [docs/operations.md](docs/operations.md#configuration).

### Frontend
```bash
cd frontend
npm install
npm run dev            # http://localhost:9000
npm run build          # production build → dist/spa/
```

---

## Tests

```bash
cd backend
pytest tests/
```

All new backend features must include tests. Use a temporary SQLite database for integration tests (see `tests/test_text_classifier_crud.py` for the pattern). Frontend tests: Vitest unit tests for complex store/service logic when introduced.

---

## Code Conventions

### Backend
- Python ≥ 3.11; `from __future__ import annotations` where helpful.
- Async-first: all DB calls use `AsyncSession`; no sync SQLAlchemy.
- Pydantic v2 schemas in `base_objects.py`.
- Raise `DBError` (defined in `database.py`) for database-layer failures.
- No secrets in source files — read from env via `config.py`.
- Keep routes thin: business logic in `crud.py` or service modules.

### Frontend
- Vue 3 Composition API (`<script setup>`); no Options API.
- All API types in `src/types/api.ts` must mirror backend schemas.
- API calls through `src/services/api.ts` only — no direct `axios` calls from components.
- One Pinia store per domain when state is shared across pages (currently auth only).
- Quasar components preferred over raw HTML.

### General
- No hard-coded credentials, URLs, or file paths.
- Commits: one logical change per commit.

---

## Documentation

- Public-facing API changes must be reflected in `frontend/openapi.json` (regenerate from `/openapi.json`) and `docs/api_reference.md`.
- Changes to behaviour, schema or operations must update the matching file in `docs/` (see [docs/README.md](docs/README.md)). `docs/` describes the current state; `logs/` records changes.
- New terms go to `docs/glossary.md` first.

---

## Change Log

Every non-trivial change must have a log file:

```
logs/{YYYYMMDDTHHMMSS}_{short_snake_case_description}.md
```

Contents: what changed, why, decisions made. The `logs/` directory is committed.

---

## Security (OWASP Top 10)

- **A01 Broken Access Control**: Admin routes check `user.is_superuser`. User routes never expose other users' data.
- **A02 Cryptographic Failures**: `JWT_PRIVATE_KEY`, `SECRET`, `ADMIN_PASSWORD` must be strong random values in production.
- **A03 Injection**: Use SQLAlchemy ORM / parameterised queries only — never interpolate user input into SQL.
- **A05 Security Misconfiguration**: Set `PRODUCTION=true` in production; CORS middleware is then omitted (handled by reverse proxy).
- **A07 Auth Failures**: Keep JWT lifetime short in production.

---

## Data Rules

- The DB is authoritative for tasks. Prompt import (`POST /api/admin/tasks/import-prompts`) overwrites DB task content: [docs/task_definitions.md](docs/task_definitions.md#sources-of-truth).
- Annotations store class IDs. Never rename or remove a class ID after annotation has started.
- Back up the DB before manual edits: [docs/operations.md](docs/operations.md#backups).
- Formats: tasks [docs/task_definitions.md](docs/task_definitions.md), texts / GT / LLM uploads [docs/operations.md](docs/operations.md#admin-data-uploads).

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Task selection UX | User picks ≤ 6 tasks; texts served one-by-one | Manageable cognitive load |
| Task storage | DB (imported from `prompts/*.md`, then edited in the DB) | Runtime admin control |
| Sampling | Fill-to-target with in-memory reservations | Even coverage; single worker |
| Text storage | Full JSON blob + extracted fields | Preserves AI labels for benchmarking |
| Duplicate upload | Upsert by `id` | Safe re-import |
| Registration | Open | Low friction for annotators |
