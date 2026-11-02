# semant_text_cl_app

Collects human text-classification annotations for benchmarking AI classifiers.

Documentation: [docs/README.md](docs/README.md). Agent and contributor rules: [AGENTS.md](AGENTS.md).

## Stack

- Backend: FastAPI, async SQLAlchemy, fastapi-users, Pydantic v2
- Frontend: Quasar (Vue 3, TypeScript)
- DB: SQLite by default; `DATABASE_URL` can point to PostgreSQL

## Development

```bash
cd backend
pip install -r requirements.txt
ALLOWED_ORIGIN=http://localhost:9005 python run.py        # http://localhost:8003
```

```bash
cd frontend
npm install
API_URL=http://localhost:8003 npx quasar dev -p 9005
```

`API_URL` is injected at build time (`quasar.config.js` `build.env`).

## Deployment

- Build: `API_URL=https://host npm run build` → `frontend/dist/spa/`. Either serve it separately, or copy it to `backend/static/` so the backend serves it.
- Docker: `cd deploy && docker compose up --build` (backend `:8002`, frontend `:9000`).

Details, config and backups: [docs/operations.md](docs/operations.md). API: [docs/api_reference.md](docs/api_reference.md).
