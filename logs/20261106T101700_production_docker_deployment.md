# Production Docker deployment on pchradis2

## What changed
- Tag `v0.1` (c52cb3c) created and pushed. This is the first tagged release.
- The app now runs as a Docker container behind the host's Traefik proxy at
  https://pchradis2.fit.vutbr.cz/ (root path). It replaces the retired Potato
  annotator there.
- The deployment root is `~/projects/2026-09-21_potato/deploy/text_classification/`.
  That is outside this repo, like the other stacks on the host.
- The dev server (`python run.py` on :8003) was stopped. `backend/database.sqlite`
  was copied with `sqlite3 .backup` into the deployment's `state/`. That copy is
  now the authoritative DB. `backend/database.sqlite` here is stale.

## Decisions
- One image, multi-stage: the repo is cloned at the tag over HTTPS (the repo is
  public), the Quasar SPA is built with `API_URL=https://pchradis2.fit.vutbr.cz`,
  and FastAPI serves the SPA and the API from one origin, with `PRODUCTION=true`
  and no CORS.
- `prompts/` is copied to `/prompts` so that the prompt import works. This fixes
  the known issue with the old `deploy/` images.
- uvicorn runs directly with `--workers 1`, no `--reload`, and proxy headers on.
- New random `JWT_PRIVATE_KEY` and `SECRET` values, so existing logins expired once.
- The local debug port is `127.0.0.1:8013`, because 8010 is in use on the host.
