# Architecture

The app collects human annotations of texts for benchmarking AI classifiers. Terms: [glossary.md](glossary.md).

```mermaid
flowchart LR
    A[Annotator] --> F[Quasar SPA]
    Admin --> F
    F -->|REST, JWT bearer| API[FastAPI]
    API --> DB[(SQLite / PostgreSQL)]
    API --> R[ReservationStore<br/>in memory]
    API -.->|import| P[prompts/*.md]
    J[reliability loop<br/>every 30 min] --> DB
```

- Backend: FastAPI, async SQLAlchemy, fastapi-users (JWT). One process; reservations and the reliability loop are in memory.
- Frontend: Quasar (Vue 3, `<script setup>`), Axios through `src/services/api.ts`.
- Optional: the backend serves the built SPA from `STATIC_PATH`.

Module map: [code_map.md](code_map.md). Tables: [data_model.md](data_model.md).

## Annotation flow

```mermaid
sequenceDiagram
    participant U as Annotator
    participant SPA
    participant API
    participant DB

    U->>SPA: choose task selection (1–6 tasks), stored in localStorage
    SPA->>API: POST /api/texts/next {task_ids}
    API->>DB: coverage per (text, task)
    API->>API: fill-to-target pick, reserve text
    API-->>SPA: text (204 if no active text)
    U->>SPA: answer each task, one task per step
    SPA->>API: POST /api/annotations
    API->>DB: validate, compute points, insert one annotation per task
    API->>API: release reservation
    API-->>SPA: {points: {task_id: float}}
```

Sampling, points and reliability: [sampling_and_scoring.md](sampling_and_scoring.md).

## Task flow

Prompt files → import → DB task → edited in Admin → Tasks. The DB is authoritative; re-import overwrites it. See [task_definitions.md](task_definitions.md).

## Frontend pages

| Route | Page | Content |
|---|---|---|
| `/login` | `LoginPage.vue` | Login and registration (`display_name` optional). |
| `/classify` | `ClassificationPage.vue` | Task selection dialog, one task per step, summary panel, calibration feedback panel (inactive). |
| `/leaderboard` | `LeaderboardPage.vue` | Own stats, overall leaderboard (weekly / all time), per-task leaderboards. |
| `/admin` | `AdminPage.vue` | Tabs: Tasks, Import, Texts, Coverage, Reliability. Superuser only (enforced by the API). |
