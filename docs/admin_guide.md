# Administrator Guide

## Importing prompt tasks

1. Log in as a superuser.
2. Open the Admin page.
3. Click **Import prompts/*.md as tasks**.
4. Review imported task definitions before annotation begins.

The import operation upserts tasks by ID, so re-importing a prompt updates the existing database task while preserving the same task ID.

## Editing tasks in the application

On the Admin page, each task can be edited in place:

- **Task name**: Short annotator-facing label.
- **Enabled**: Disabled tasks are hidden from annotators and rejected in submissions.
- **Multi-choice**: Switches the annotation widget between radio buttons and checkboxes.
- **Max choices**: Limits checkbox selections for multi-choice tasks.
- **Prompt markdown**: Full task instructions shown or stored for downstream context.
- **Choices**: Class IDs and English/Czech labels.

After editing, click **Save task**. The frontend validates required fields and duplicate class IDs before sending the task to the API.

## Uploading texts

Paste JSONL into the Admin page text uploader. Each line must include:

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable unique text identifier. |
| `text` | string | Text shown to annotators. |
| `language` | string | ISO 639-3 language code such as `eng` or `ces`. |

Any additional JSON fields are stored unchanged for export and analysis.

## Operational checklist

- Import prompts after changing files in `prompts/`.
- Confirm that tasks expected to allow two answers are marked **Multi-choice**.
- Keep class IDs stable once annotation has started.
- Disable rather than delete tasks if historical annotations should remain interpretable.
- Use strong production values for authentication secrets and admin credentials.
