# Code Map

## Backend (`backend/text_classifier/`)

| Module | Contents |
|---|---|
| `config.py` | `Config` (env settings); see [operations.md](operations.md#configuration). |
| `database.py` | Engine, session, `User` table, `DBError`. |
| `db_model.py` | `Task`, `TextItem`, `Annotation`, `AnnotationType`, `UserReliability`. |
| `base_objects.py` | Pydantic request and response schemas; `TaskDefinition` validator. |
| `users.py` | fastapi-users setup, `current_active_user`, JWT strategy. |
| `main.py` | App, routers, CORS, static mount, startup (`create_all`, admin user), `_reliability_loop`. |
| `routes.py` | `api_route` (`/api`) and `admin_route` (`/api/admin`). Admin checks `user.is_superuser` in each handler. |
| `crud.py` | All DB logic; sections below. |
| `reservations.py` | `ReservationStore`, global `reservations`. |
| `reliability.py` | `run_reliability_job` and the metric functions. |
| `prompt_parser.py` | `load_prompts`, `parse_prompt_file`. |

`crud.py` sections, in file order:

| Section | Functions |
|---|---|
| Helpers | `_display_name`, `_scarcity_multiplier` |
| Task CRUD | `upsert_task`, `set_task_state`, `list_tasks`, `list_enabled_tasks`, `get_task_multiplier` |
| Text CRUD | `upsert_text`, `list_texts`, `set_text_suspended` |
| Sampling | `get_next_text`, `_pick_fill_text`, `_score_text`, `_annotators_per_text_task`, `_pick_calibration_text` (unused), `coverage_stats` |
| Points | `_compute_points` |
| Annotation CRUD | `save_annotations`, `bulk_upsert_annotations`, `set_annotation_type`, `get_gt_for_text_tasks` |
| Stats & leaderboard | `my_stats`, `leaderboard`, `leaderboard_overall`, `global_stats`, `get_text_annotations` |
| Reliability queries | `get_reliability` |

Tests (`backend/tests/`): `test_text_classifier_crud.py` (CRUD and API, temporary SQLite), `test_sampling.py` (fill-to-target, reservations), `test_prompt_parser.py`.

## Frontend (`frontend/src/`)

| Path | Contents |
|---|---|
| `services/api.ts` | `ApiService`: the only place that calls Axios. |
| `types/api.ts` | TypeScript mirrors of the backend schemas. |
| `boot/axios.ts` | Axios instance, `API_URL`, bearer token header. |
| `stores/auth-store.ts` | The only Pinia store (auth). Task and annotation state live in `ClassificationPage.vue`. |
| `pages/` | One page per route; see [architecture.md](architecture.md#frontend-pages). |
| `components/TaskSelectionDialog.vue` | Task selection, multiplier badge. |
| `components/MarkdownView.vue` | Renders task prompts. |

Unused scaffold: `pages/IndexPage.vue`, `pages/TaskSelectionPage.vue`, `components/ExampleComponent.vue`, `components/EssentialLink.vue`, `components/models.ts`, `stores/example-store.ts`.

## Adding an endpoint

1. Schema in `base_objects.py`.
2. DB logic in `crud.py` (async, ORM only).
3. Thin handler in `routes.py`; add the `is_superuser` check for admin routes.
4. Test in `backend/tests/`.
5. Type in `frontend/src/types/api.ts`, method in `services/api.ts`.
6. Regenerate `frontend/openapi.json` from `/openapi.json`; update [api_reference.md](api_reference.md).
7. Add a `logs/` entry.
