# Documentation restructure

## What changed
- New: `docs/README.md` (index), `docs/glossary.md` (naming), `docs/data_model.md`, `docs/sampling_and_scoring.md` (current state), `docs/operations.md`, `docs/code_map.md`.
- Rewritten against the current code: `docs/architecture.md`, `docs/api_reference.md`, `docs/task_definitions.md` (now covers sources of truth and the label/prompt rule), `docs/admin_guide.md`.
- Moved to `docs/history/`: `rebuild_task.md`, `SAMPLING_AND_SCORING.md` (→ `SAMPLING_AND_SCORING_plan.md`), `TASK_PROGRESS.md`, `UI_IMPROVEMENTS.md`, `frontend/{IMPLEMENTATION_SUMMARY,PROJECT_README,QUICK_START}.md`.
- `README.md`: shortened; links the docs; default port corrected to 8003.
- `AGENTS.md`: links the docs index and glossary; env table replaced by a link; port 8003; stores rule matches reality; adds data rules; drops the `rebuild_task.md` reference.

## Decisions
- `docs/` = current state, `logs/` = changes, `docs/history/` = superseded material.
- Naming is fixed in `glossary.md` and follows code identifiers (task, class, class ID, label_cs, task prompt, prompt file, text, annotation, coverage, reservation, points, score, reliability).
- `task_definitions.md` was kept as the filename (it now also covers task lifecycle) rather than adding a separate lifecycle file.

## Gaps found while documenting (not fixed)
- The classification UI renders `label_en`, while task prompts use `label_cs`.
- The Docker backend image does not include `prompts/`, so prompt import fails in the container.
- `repeat_probability` and `Annotation.weight` are unused; `ds_sensitivity` is never computed.
- Deleting a task leaves its annotations orphaned.
