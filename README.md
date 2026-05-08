# semant_text_cl_app

Human-in-the-loop text classification app for creating benchmark labels.

## Stack
- Backend: FastAPI, SQLAlchemy async, fastapi-users, Pydantic v2
- Frontend: Quasar (Vue 3 + TypeScript)
- DB: SQLite by default (`DATABASE_URL` can point to PostgreSQL)

## Backend (dev)
```bash
cd backend
pip install -r requirements.txt
PORT=8005 ALLOWED_ORIGIN=http://localhost:9005 python run.py
```
Backend defaults to `http://localhost:8002` if `PORT` is not set.

## Frontend (dev)
```bash
cd frontend
npm install
API_URL=http://localhost:8005 quasar dev -p 9005 -h 0.0.0.0
```
`API_URL` is injected by Quasar build config (`build.env`) and used by axios boot file.

## Frontend build with custom backend URL
```bash
cd frontend
API_URL=http://api.example.com:8005 npm run build
```
The compiled app will call that API URL at runtime.

## Main API
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `POST /api/texts/next`
- `POST /api/annotations`
- `GET /api/stats/me`
- `GET /api/stats/leaderboard/{task_id}`
- `POST /api/admin/tasks`
- `PATCH /api/admin/tasks/{task_id}`
- `POST /api/admin/texts`
- `POST /api/admin/tasks/import-prompts`

## Notes
- Task definitions are stored in DB and support single-choice or multi-choice labels.
- Text uploads are JSONL; full row JSON is stored for downstream benchmarking/export.

## Docker compose deployment
```bash
cd deploy
docker compose up --build
```
- Frontend: `http://localhost:9000`
- Backend: `http://localhost:8002`

Use `deploy/frontend.Dockerfile` build arg to set API URL:
```bash
docker build -f deploy/frontend.Dockerfile --build-arg API_URL=http://localhost:8002 -t text-classifier-frontend .
```
