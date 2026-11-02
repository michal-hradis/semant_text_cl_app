# Czech class labels in the classification UI

## What changed
- `frontend/src/pages/ClassificationPage.vue`:
  - Radio buttons and checkboxes show `label_cs` instead of `label_en`.
  - The summary panel and the calibration feedback show `label_cs` instead of raw class IDs (new helper `classLabels`; falls back to the ID if a class is missing).
- `docs/task_definitions.md` and `docs/README.md` updated.

## Why
The Czech task prompts refer to classes by `label_cs`, but annotators saw English labels and IDs.

## Decisions
- Submitted data is unchanged: annotations still store class IDs.
- The calibration match is still computed on IDs; only the display uses labels.
