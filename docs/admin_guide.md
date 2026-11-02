# Admin Guide

The Admin page (`/admin`) is visible to superusers. Terms: [glossary.md](glossary.md).

## Tasks tab

- Create, edit, enable/disable or delete tasks. The task ID is editable only on creation.
- The editor holds: name, enabled, multi-choice, max choices, task prompt (markdown), classes (ID, English label, Czech label, description), sampling settings.
- Class descriptions are shown as `(i)` tooltips to annotators.
- Keep Czech labels and task prompt consistent: [task_definitions.md](task_definitions.md#labels-and-prompts).

## Import tab

- **Import prompts/*.md**: overwrites the name, prompt, classes and limits of every task that has a prompt file. Do not use it on the production DB unless the prompt files hold the wanted content; see [task_definitions.md](task_definitions.md#sources-of-truth).
- **GT upload** and **LLM upload**: JSONL `{text_id, task_id, selected_classes}`.

## Texts tab

- Upload JSONL (`id`, `text`, `language`, plus any extra fields, all kept in `raw_json`). Re-uploading an ID updates the text.
- Search, page through texts, view a text's annotations, suspend or unsuspend.

## Coverage tab

Per enabled task: complete, partial and untouched texts, missing annotations up to the target, and current reservations. Change `target_coverage` in the task editor.

## Reliability tab

Per (annotator, task): pairwise agreement, Cohen's κ, Krippendorff's α. **Recompute** runs the job immediately. Annotators with fewer than 5 shared texts have no row. Definitions: [sampling_and_scoring.md](sampling_and_scoring.md#reliability).

## Checklist

- Back up the DB before bulk changes ([operations.md](operations.md#backups)).
- Never change a class ID after annotation has started.
- Disable tasks and suspend texts instead of deleting them.
- Set strong `JWT_PRIVATE_KEY`, `SECRET` and `ADMIN_PASSWORD` in production.
