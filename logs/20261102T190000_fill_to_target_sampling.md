# Fill-to-target text sampling, soft reservations, coverage view

## What changed
- `crud.get_next_text` now uses a **fill-up-to-target** rule in place of the
  random / repeat-probability rule. `_pick_repeat_text` and `_pick_random_text`
  were removed.
  - For each active text, score = Σ over the user's selected tasks k of
    `1 + n(t,k)`, counted only where `n(t,k) < target_k` and the user has not
    already annotated (t, k). `n(t,k)` = distinct users with `user`-type
    annotations plus users currently holding a soft reservation.
  - The best score wins, with a random tie-break. If every score is 0 (all
    saturated), it falls back to a random text the user has not seen, then to
    any random active text.
  - `target_k` = `Task.target_coverage` (set to 4 for all tasks in the DB).
    `repeat_probability` is no longer used by the sampler.
- New `text_classifier/reservations.py`: an in-memory `ReservationStore`. Each
  user has one reservation of (text, tasks) with a TTL
  (`RESERVATION_TTL_SECONDS`, default 900). It is replaced on the next request
  and released on `POST /api/annotations`.
- New admin endpoint `GET /api/admin/coverage` (`crud.coverage_stats`): per
  enabled task, the counts of complete, partial and untouched active texts,
  missing annotations and in-progress reservations.
- Frontend: a new Admin "Coverage" tab, plus the `TaskCoverage` type and
  `apiService.getAdminCoverage`. The default target for new tasks is 4.
- `frontend/openapi.json` regenerated.
- Tests: `backend/tests/test_sampling.py`.

## Decisions
- Overshooting the target and repeat annotations by the same user are acceptable
  (per the request). Repeats are only served when nothing better is left.
- `1 + n` prefers finishing texts before starting new ones.
- With < 1000 texts, scoring every text in Python on every request is cheap
  (one grouped query).
- Reservations live in memory and are correct only with a single worker. This is
  acceptable because reservations are only a hint.
- Calibration stays disabled, as before. The pre-existing test
  `test_bulk_gt_annotations_and_calibration_path` still fails for that reason.
