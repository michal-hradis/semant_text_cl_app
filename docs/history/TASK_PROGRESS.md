# Task Progress — Sampling & Scoring System

This file tracks implementation progress for the sampling, calibration, and scoring system described in `SAMPLING_AND_SCORING.md`.

---

## Phase Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Schema & annotation types | ✅ Complete |
| 2 | GT & LLM upload endpoints | ✅ Complete |
| 3 | Sampling algorithm rewrite | ✅ Complete |
| 4 | Point calculation at submit | ✅ Complete |
| 5 | Reliability background job | ✅ Complete |
| 6 | Frontend updates | ❌ Not started |

---

## Phase 1 — Schema & Annotation Types

**Status**: Complete  
**Completed**: 2026-05-31

### Changes
- `db_model.py`: Added `AnnotationType` enum (`user`, `ground_truth`, `llm`); added 5 sampling config columns to `Task`; added `annotation_type`, `weight`, `points_earned` to `Annotation`; added new `UserReliability` table.
- `base_objects.py`: Added `TaskSamplingConfig`, extended `TaskDefinition` with sampling config + `current_multiplier`; extended `NextTextResponse` with `calibration_task_ids`; added `AnnotationTypeValue`, `BulkAnnotationItem`, `UserReliabilityResponse`, `MyStats`.
- `requirements.txt`: Added `krippendorff`, `numpy`, `scikit-learn`, `scipy`.

### Decisions
- `current_multiplier` is a computed field, excluded from DB upsert via `_TASK_READONLY` set.
- Sampling config defaults: `calib_ratio_initial=0.30`, `calib_initial_count=20`, `calib_ratio_ongoing=0.10`, `repeat_probability=0.20`, `target_coverage=3`.

---

## Phase 2 — GT & LLM Upload Endpoints

**Status**: Complete  
**Completed**: 2026-05-31

### Changes
- `routes.py`: Added `POST /api/admin/ground-truth`, `POST /api/admin/llm-annotations`, `PATCH /api/admin/annotations/{id}`.
- `crud.py`: Added `bulk_upsert_annotations()`, `set_annotation_type()`.
- Bulk format: JSONL with `text_id`, `task_id`, `selected_classes` fields.
- GT/LLM annotations are attributed to the uploading admin user.

---

## Phase 3 — Sampling Algorithm Rewrite

**Status**: Complete  
**Completed**: 2026-05-31

### Changes
- `crud.py`: Replaced single-path `get_next_text` with 3-path algorithm:
  1. **Calibration check**: Per task, stochastic based on `calib_ratio_initial` / `calib_ratio_ongoing` (threshold at `calib_initial_count`). Picks a GT-annotated text the user hasn't seen.
  2. **Repeat**: Random check with `repeat_probability` → picks a text annotated by others but not this user (random from top-10 least-covered).
  3. **New text**: Least-covered text the user hasn't seen (original algorithm).
- `get_next_text` now returns `(TextItem | None, list[str])` — the second element is `calibration_task_ids`.
- `routes.py`: Updated `POST /api/texts/next` to forward `calibration_task_ids` in response.
- Test updated: unpacks tuple return value.

---

## Phase 4 — Point Calculation at Submit

**Status**: Complete  
**Completed**: 2026-05-31

### Changes
- `crud.py`: Added `_compute_points()`. Formula: `base=1 + K × max(0, A - E)` where:
  - `K = 30 × scarcity_multiplier` (scarcity = 1 + max(0, 1 - avg_coverage/target))
  - `E = pairwise_agreement from UserReliability` (default 0.5)
  - `A = 1.0` if matches GT; else weighted majority agreement with other user annotations; 0.0 if first annotator
- `save_annotations()` now accepts optional `annotation_type` (default `user`) and returns `{task_id: float}` points dict.
- `routes.py`: `POST /api/annotations` now returns `{"points": {task_id: float}}` (was 201 empty).

---

## Phase 5 — Reliability Background Job

**Status**: Complete  
**Completed**: 2026-05-31

### Changes
- `reliability.py` (new): Functions `_pairwise_agreement`, `_cohens_kappa`, `_krippendorffs_alpha`, `run_reliability_job`.
  - Uses `krippendorff` library and `sklearn.metrics.cohen_kappa_score`.
  - Only runs for users with ≥5 annotations per task.
  - Stores results in `UserReliability` table (upsert by user+task).
- `main.py`: Replaced deprecated `@app.on_event("startup")` with `lifespan` context manager; added `_reliability_loop()` background asyncio task running every 30 minutes.
- `routes.py`: Added `GET /api/admin/irr` and `POST /api/admin/irr/recompute`.
- `crud.py`: Added `get_reliability()` query helper.

---

## Phase 6 — Frontend Updates

**Status**: Not started

### Planned changes
- `src/types/api.ts`: Add `calibration_task_ids` to `NextTextResponse`, `score` to `LeaderboardEntry`, `current_multiplier` to `TaskDefinition`, add `MyStats` type.
- `src/pages/ClassificationPage.vue`: Show calibration feedback panel after submit when `calibration_task_ids` is non-empty.
- `src/pages/LeaderboardPage.vue`: Add score column.
- `src/pages/AdminPage.vue`: Add "Reliability" tab with IRR table.
- Task selection: Show multiplier badge next to each task.

---

## Open Issues / Notes

- The `ds_sensitivity` field in `UserReliability` is not yet computed (Dawid-Skene is complex; left as `NULL`).
- Points for GT/LLM annotations are `NULL` (intentional).
- Frontend still uses old `POST /api/annotations` response format (empty 201). Will need updating in Phase 6.
- The `count` field in admin text upload route was removed (older routes.py had it, new one doesn't return it). Fixed: `return {'imported': count}`.
