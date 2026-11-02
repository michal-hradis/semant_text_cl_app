# API Reference

Source: `backend/text_classifier/routes.py`, schemas in `base_objects.py`, full spec in `frontend/openapi.json`. Terms: [glossary.md](glossary.md).

Auth: `Authorization: Bearer <JWT>` from `POST /auth/jwt/login`. "user" = any logged-in user; "admin" = `is_superuser`.

## Auth (fastapi-users)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/auth/jwt/login` | Form `username`, `password` → `{access_token}`. |
| `POST` | `/auth/jwt/logout` | |
| `POST` | `/auth/register` | `{email, password, display_name?}`; open registration. |
| `GET`, `PATCH` | `/users/me` | Current user. |

## Annotator API (`/api`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/tasks` | none | Enabled tasks, with `current_multiplier`. |
| `GET` | `/api/tasks/{task_id}` | none | One enabled task. |
| `POST` | `/api/texts/next` | user | `{task_ids: [1–6]}` → `NextTextResponse`, or 204 if there is no active text. Reserves the text. |
| `POST` | `/api/annotations` | user | `AnnotationSubmit` → `{points: {task_id: float}}`. Releases the reservation. 400 for an unknown or disabled task or invalid classes. |
| `GET` | `/api/texts/{text_id}/ground-truth?task_ids=…` | user | `{task_id: [class_id]}` for GT annotations. |
| `GET` | `/api/stats/me` | user | `{total, per_task, score, per_task_score}`. |
| `GET` | `/api/stats/global` | none | `{total_annotations, per_task: [{task_id, task_name, count}]}`. |
| `GET` | `/api/stats/leaderboard?since_days=N` | none | Top 20 `LeaderboardEntry`, all tasks. |
| `GET` | `/api/stats/leaderboard/{task_id}?since_days=N` | none | Top 20 for one task. |

## Admin API (`/api/admin`, admin)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/tasks` | All tasks, including disabled ones. |
| `POST` | `/tasks` | Upsert a `TaskDefinition`. |
| `PUT` | `/tasks/{task_id}` | Update; the path ID must equal the body ID. |
| `PATCH` | `/tasks/{task_id}` | `{enabled?: bool, deleted?: bool}`. |
| `POST` | `/tasks/import-prompts` | Upsert all `prompts/*.md`. **Overwrites DB task content**; see [task_definitions.md](task_definitions.md#sources-of-truth). |
| `POST` | `/texts` | JSONL body (`text/plain`), rows `{id, text, language, …}` → `{imported}`. |
| `GET` | `/texts?page=&q=&page_size=&task_id=` | Paginated list; `annotation_count` counts `user` annotations (for `task_id` if given). |
| `GET` | `/texts/{text_id}/annotations?task_id=` | All annotations of a text, all types. |
| `PATCH` | `/texts/{text_id}` | `{suspended: bool}`. |
| `POST` | `/ground-truth` | JSONL `{text_id, task_id, selected_classes}` → GT annotations. |
| `POST` | `/llm-annotations` | Same format → LLM annotations. |
| `PATCH` | `/annotations/{annotation_id}` | `{annotation_type: "ground_truth" \| "llm"}`. |
| `GET` | `/coverage` | `TaskCoverage` per enabled task. |
| `GET` | `/irr` | All `UserReliability` rows. |
| `POST` | `/irr/recompute` | Run the reliability job now. |

## Main schemas

`TaskDefinition`: `id, name, description_md, multi_choice, max_choices, enabled, classes[{id, label_en, label_cs, description?}], calib_ratio_initial, calib_initial_count, calib_ratio_ongoing, repeat_probability, target_coverage (default 3), current_multiplier?` (read-only). Meaning of each field: [data_model.md](data_model.md#tasks-task).

`NextTextResponse`: `{id, text, language, calibration_task_ids}`; `calibration_task_ids` is always `[]` while calibration is disabled.

`AnnotationSubmit`:
```json
{"text_id": "t1", "annotations": [
  {"task_id": "style", "selected_classes": ["formal"],
   "start_time": "2026-05-30T12:00:00Z", "end_time": "2026-05-30T12:00:10Z"}]}
```

`LeaderboardEntry`: `{user_id, display_name, count, score, reliability}`; `reliability` = `pairwise_agreement` (mean over tasks for the overall board), `null` before the first job run.

`TaskCoverage`: `{task_id, task_name, target, active_texts, complete_texts, partial_texts, untouched_texts, missing_annotations, pending_reservations}`.

`UserReliabilityResponse`: `{user_id, display_name, task_id, annotation_count, pairwise_agreement, cohens_kappa, krippendorffs_alpha, ds_sensitivity, computed_at}`.
