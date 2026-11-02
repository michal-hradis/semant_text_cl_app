# Glossary and Naming

Canonical terms for code, docs, logs and UI text. Where code and prose names differ, the code identifier is given in backticks.

## Core objects

| Term | Code | Definition | Do not use |
|---|---|---|---|
| task | `Task`, `task_id` | One classification dimension (e.g. `style`) with its own classes and prompt. | dimension, question |
| class | `TaskClass`, `classes[]` | One allowed answer of a task. | choice, option, category, label (as the object) |
| class ID | `TaskClass.id` | Stable English identifier stored in annotations. Never renamed once annotation has started. | class name |
| class label | `label_en`, `label_cs` | Display string of a class. `label_cs` = Czech label, `label_en` = English label. Labels may change; IDs may not. | — |
| task prompt | `Task.description_md` | Markdown instructions stored in the DB and shown to annotators. | description, instructions |
| prompt file | `prompts/{task_id}.md` | Source markdown imported into a task. English, uses class IDs. | prompt (alone) |
| text | `TextItem`, `text_id` | One unit to classify, uploaded from JSONL. | passage, document, chunk, item |
| raw JSON | `TextItem.raw_json` | The full uploaded JSONL row. | metadata |
| annotation | `Annotation` | One record: (annotator, text, task) → `selected_classes`. One submit creates one annotation per selected task. | label, answer, vote |
| annotation type | `AnnotationType` | `user` (annotator), `ground_truth` (GT), `llm` (LLM output). | source, kind |
| GT | `ground_truth` | Reference annotation uploaded or promoted by an admin. | gold, reference |

## People

| Term | Code | Definition |
|---|---|---|
| user | `User` | Any account. |
| annotator | `User` with `user` annotations | A user who classifies texts. |
| admin | `User.is_superuser = true` | Has access to `/api/admin/*`. |

## States

| Term | Code | Definition |
|---|---|---|
| enabled task | `Task.enabled = true` | Visible to annotators; accepted on submit. |
| active text | `TextItem.suspended = false` | Can be served by the sampler. |
| suspended text | `TextItem.suspended = true` | Hidden from the sampler; data kept. |
| task selection | `selected_tasks` (localStorage), `NextTextRequest.task_ids` | The 1–6 tasks an annotator chose to work on. |

## Sampling and scoring

| Term | Code | Definition |
|---|---|---|
| sampler | `crud.get_next_text` | Picks the next text for an annotator and a task selection. |
| coverage | `n(text, task)` | Number of distinct annotators with `user` annotations on (text, task). |
| target coverage | `Task.target_coverage` | Desired coverage per (text, task). |
| complete / partial / untouched text | `coverage_stats` | Coverage ≥ target / 0 < coverage < target / coverage = 0, per task. |
| fill-to-target | `_pick_fill_text`, `_score_text` | Current sampling rule; see [sampling_and_scoring.md](sampling_and_scoring.md). |
| reservation | `ReservationStore` | In-memory hold of (text, tasks) for one annotator while they annotate. Counts as pending coverage. |
| calibration | `calib_*`, `calibration_task_ids` | Serving GT texts to measure annotators. Currently disabled. |
| scarcity multiplier | `_scarcity_multiplier`, `current_multiplier` | 1.0–2.0 factor; higher when a task's average coverage is below target. |
| points | `Annotation.points_earned` | Value awarded to one `user` annotation at submit time. |
| score | `sum(points_earned)` | Sum of points; used to rank leaderboards. |
| reliability | `UserReliability` | Per (annotator, task) agreement metrics. In the UI, "reliability" means `pairwise_agreement`. |
| IRR | `/api/admin/irr` | Inter-rater reliability; the same data as reliability. |
