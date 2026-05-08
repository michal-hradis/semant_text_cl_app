# API URL env fix and deploy setup

- Fixed frontend API URL injection by wiring `API_URL` through Quasar `build.env` and using it in axios boot.
- Updated frontend default API URL to `http://localhost:8002`.
- Documented backend/frontend URL overrides for development and frontend compilation.
- Added `deploy/` with backend/frontend Dockerfiles and docker-compose.yml for local deployment.
