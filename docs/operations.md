# Operations

## Configuration

`backend/text_classifier/config.py` (pydantic-settings). Values come from environment variables, then from `.env` in the working directory (`backend/.env`, gitignored, mode 600; put secrets such as `OPENAI_API_KEY` there), then the defaults below.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///database.sqlite` | Relative to the working directory (`backend/`). |
| `PORT` | `8003` | Docker image sets `8002`. |
| `PRODUCTION` | `false` | `true` disables CORS middleware (a reverse proxy handles it). |
| `ALLOWED_ORIGIN` | `http://pchradis2.fit.vutbr.cz:9005` | CORS origin in dev. |
| `JWT_PRIVATE_KEY`, `SECRET` | dev values | Must be replaced in production. |
| `ADMIN`, `ADMIN_PASSWORD` | `admin@example.com`, `admin123` | Superuser created at first start. |
| `STATIC_PATH` | `./static` | If the directory exists, the backend serves the built SPA at `/`. |
| `RESERVATION_TTL_SECONDS` | `900` | See [sampling_and_scoring.md](sampling_and_scoring.md). |
| `VOICE_COMMENTS_ENABLED` | `true` | `false` hides the recording button and rejects uploads. |
| `VOICE_AUDIO_PATH` | `./voice_audio` | Audio file directory; persist it (Docker volume) and back it up. |
| `VOICE_MAX_SECONDS` | `300` | Maximum recording length per text. |
| `VOICE_MAX_BYTES` | `26214400` | Upload limit (25 MB, the OpenAI limit). |
| `TRANSCRIBE_ENABLED` | `false` | Turn on OpenAI transcription of voice comments; off, audio is only stored and stays `pending`. |
| `OPENAI_API_KEY` | empty | Needed for transcription; without it voice comments stay `pending`. |
| `OPENAI_TRANSCRIBE_MODEL` | `gpt-4o-transcribe` | `whisper-1` also returns segment timestamps. |
| `TRANSCRIBE_INTERVAL_SECONDS`, `TRANSCRIBE_MAX_ATTEMPTS` | `30`, `3` | Transcription loop; see [voice_comments.md](voice_comments.md#transcription). |

Frontend: `API_URL` at build/dev time (`quasar.config.js` `build.env`; fallback in `src/boot/axios.ts`).

## Running

```bash
cd backend && python run.py                       # uvicorn, reload=True, single worker
cd frontend && API_URL=http://localhost:8003 npm run dev
cd frontend && API_URL=https://host npm run build # → dist/spa/
```

Single-backend deployment: copy `frontend/dist/spa/*` to `backend/static/` and run the backend; the SPA and API share one origin.

Docker: `cd deploy && docker compose up --build` (backend `:8002`, frontend nginx `:9000`). Known issue: the backend image copies only `backend/`, so `prompts/` is missing and the prompt import fails inside the container.

Production (pchradis2.fit.vutbr.cz): a single container built from a git tag, behind Traefik at `https://pchradis2.fit.vutbr.cz/`. The deployment root is `~/projects/2026-09-21_potato/deploy/text_classification/` on that host (not in this repo). It contains the Dockerfile, `docker-compose.yml`, `.deploy/.env` (secrets) and `state/` (`database.sqlite`, `voice_audio/`). Its `README.md` covers releasing a new tag, backups and password resets.

Run one worker only: reservations, the reliability loop and the transcription loop live in process memory.

Microphone recording requires the SPA to be served over HTTPS (or localhost).

## Backups

SQLite: copy with the online backup API, not `cp`, while the app is running:

```bash
cd backend && sqlite3 database.sqlite ".backup db.bak/database.sqlite.before_<change>_<YYYYMMDD>"
```

Naming: `db.bak/database.sqlite.before_<snake_case_change>_<YYYYMMDD>`. Back up before any manual DB edit, bulk task change or schema change.

Voice comment audio lives outside the DB in `VOICE_AUDIO_PATH`; back up that directory together with the DB (for example `rsync -a voice_audio/ <backup>/voice_audio/`).

## Schema changes

There are no migrations; `create_all` adds only missing tables. For a new column on an existing DB:

```bash
sqlite3 database.sqlite "ALTER TABLE <table> ADD COLUMN <col> <TYPE> NOT NULL DEFAULT <server_default>"
```

Keep the model's `server_default` equal to the SQL default. Record the change in a `logs/` entry.

## Scripts (`backend/`)

| Script | Purpose |
|---|---|
| `run.py` | Start uvicorn on `PORT`. |
| `reset_password.py <email> [password]` | Set a user's password; uses `DATABASE_URL`. |
| `seed_test_data.py [--texts N] [--db PATH]` | Fill a dev DB with test users, tasks, texts, GT and annotations. Do not run against production. |
| `add_random_column.py --db-url sqlite:///…` | Rewrite `texts.random_order` with fresh random values (sync URL). |

## Admin data uploads

All uploads are JSONL and upsert.

| Data | Endpoint / UI | Row fields |
|---|---|---|
| texts | `POST /api/admin/texts`, Admin → Texts | `id`, `text`, `language`, any extra fields |
| GT | `POST /api/admin/ground-truth`, Admin → Import | `text_id`, `task_id`, `selected_classes` |
| LLM | `POST /api/admin/llm-annotations`, Admin → Import | `text_id`, `task_id`, `selected_classes` |

`selected_classes` in GT and LLM uploads are class IDs and are not validated against the task.

## Tests

```bash
cd backend && pytest tests/
```

Known failure: `test_bulk_gt_annotations_and_calibration_path` (calibration is disabled).
