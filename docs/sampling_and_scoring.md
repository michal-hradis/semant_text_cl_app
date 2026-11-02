# Sampling and Scoring

The current behaviour. Code: `backend/text_classifier/crud.py`, `reservations.py`, `reliability.py`. Terms: [glossary.md](glossary.md). The original design plan, partly superseded, is in [history/SAMPLING_AND_SCORING_plan.md](history/SAMPLING_AND_SCORING_plan.md).

## Status

| Feature | State |
|---|---|
| Fill-to-target sampling | active |
| Reservations | active; in-memory, correct only with a single worker |
| Points and scarcity multiplier | active |
| Reliability job | active; runs every 30 min and on demand |
| Calibration (GT texts served) | **disabled** (commented out in `get_next_text`); `calibration_task_ids` is always `[]` |
| `repeat_probability` | unused |
| `Annotation.weight` update | not implemented (always 1.0) |
| Dawid-Skene (`ds_sensitivity`) | not implemented (`NULL`) |

## Sampler: fill-to-target

`POST /api/texts/next {task_ids}` → `crud.get_next_text(db, user_id, task_ids)`.

1. `targets = {task_id: Task.target_coverage}` for the task selection.
2. `annotators[(text, task)]` = distinct users with `user` annotations, plus users holding a reservation (other than the caller).
3. For each active text: `score = Σ over tasks k with caller ∉ annotators[(text, k)] and n < target_k of (1 + n)`, where `n = |annotators[(text, k)]|`.
4. Pick the highest score, breaking ties at random. `1 + n` prefers finishing partially covered texts and texts useful for more of the selected tasks.
5. If every score is 0 (all saturated): pick a random active text the caller has not annotated for these tasks, otherwise any random active text.
6. Reserve (caller → text, task selection) for `RESERVATION_TTL_SECONDS` (default 900).

The caller's reservation is replaced on the next request and released on `POST /api/annotations`. Reservations are lost on restart, which is harmless: they only affect sampling.

Cost: one grouped query and a Python loop over all active texts per request. This is fine at about 10³ texts; revisit at 10⁵ or more.

Coverage per task: `GET /api/admin/coverage` (Admin → Coverage).

## Points

Computed once per `user` annotation at submit (`crud._compute_points`) and never recomputed.

```
avg_coverage = user annotations of task / active texts
multiplier   = 1 + max(0, 1 − avg_coverage / target_coverage)        ∈ [1, 2]
K            = 30 × multiplier
E            = UserReliability.pairwise_agreement (default 0.5)
A            = GT exists ? (selected == GT ? 1 : 0)
             : others' user annotations exist ? weight share of the top-weighted class, if the user selected it; else 0
             : 0
points       = 1 + max(0, K × (A − E))
```

`GET /api/tasks` returns `current_multiplier` per task, shown as a badge in the task selection dialog.

Score = `sum(points_earned)`. Leaderboards (`/api/stats/leaderboard[/{task_id}]`, optional `since_days`) rank by score, then by count, and show the top 20.

## Reliability

`reliability.run_reliability_job`: run by `main._reliability_loop` every 30 min (first run 30 min after start) and by `POST /api/admin/irr/recompute`.

For each task: take `user` annotations on texts with ≥ 2 annotators. A user's answer is the sorted set of class IDs joined with `|` (exact-set match). Only users with ≥ 5 such texts get a row.

| Metric | Definition |
|---|---|
| `pairwise_agreement` | Fraction of shared texts where the user matches at least one other annotator. |
| `cohens_kappa` | Mean Cohen's κ against each other annotator with ≥ 2 shared texts. |
| `krippendorffs_alpha` | Nominal α over the texts the user annotated, all annotators. |

GT and LLM annotations are not used by the reliability job.

## Calibration (disabled)

Intended flow: with probability `calib_ratio_initial` (for the user's first `calib_initial_count` annotations of a task) or `calib_ratio_ongoing` afterwards, serve an unseen text that has GT for that task. Return those task IDs in `calibration_task_ids`; after submit the frontend fetches `GET /api/texts/{id}/ground-truth` and shows the feedback panel. `_pick_calibration_text` and the frontend panel exist. To re-enable, restore the commented block in `get_next_text` and fix the failing test `test_bulk_gt_annotations_and_calibration_path`.
