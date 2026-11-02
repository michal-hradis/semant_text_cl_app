# Documentation Index

Docs describe the current state of the app. `logs/` records individual changes. `history/` holds superseded plans.

| Document | Read when |
|---|---|
| [glossary.md](glossary.md) | Naming anything; terms used in all other docs. |
| [architecture.md](architecture.md) | First overview: components, request flow, pages. |
| [code_map.md](code_map.md) | Finding code; adding an endpoint. |
| [data_model.md](data_model.md) | Tables, invariants, schema changes. |
| [task_definitions.md](task_definitions.md) | Editing tasks, labels and prompts; prompt import. |
| [sampling_and_scoring.md](sampling_and_scoring.md) | Sampler, reservations, points, reliability, calibration status. |
| [api_reference.md](api_reference.md) | Endpoints and payloads. |
| [operations.md](operations.md) | Config, running, deploy, backups, scripts, tests. |
| [admin_guide.md](admin_guide.md) | Using the Admin page. |

## Known gaps

- Calibration disabled; `repeat_probability` unused; `Annotation.weight` never updated; `ds_sensitivity` never computed ([sampling_and_scoring.md](sampling_and_scoring.md#status)).
- No DB migrations ([data_model.md](data_model.md#schema-changes)).
- The Docker backend image lacks `prompts/` ([operations.md](operations.md#running)).
- Reservations require a single worker.

## History

| File | Content |
|---|---|
| [history/rebuild_task.md](history/rebuild_task.md) | Original rebuild spec (2026-05-08). |
| [history/SAMPLING_AND_SCORING_plan.md](history/SAMPLING_AND_SCORING_plan.md) | Sampling and scoring design plan. Sampling sections superseded by fill-to-target. |
| [history/TASK_PROGRESS.md](history/TASK_PROGRESS.md) | Progress of the sampling and scoring phases 1–6. Phase 6 was finished; see `logs/20260531T120000_phase6_frontend.md`. |
| [history/UI_IMPROVEMENTS.md](history/UI_IMPROVEMENTS.md) | UI work completed 2026-05-31. |
| [history/frontend/](history/frontend/) | Early frontend notes (`IMPLEMENTATION_SUMMARY.md`, `PROJECT_README.md`, `QUICK_START.md`). |
