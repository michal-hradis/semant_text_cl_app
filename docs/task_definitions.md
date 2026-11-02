# Task Definitions

A task holds: ID, name, task prompt, classes, choice limits, enabled flag and sampling settings. Schema: `TaskDefinition` in `backend/text_classifier/base_objects.py`. Terms: [glossary.md](glossary.md).

## Sources of truth

| Source | Language | Class references | Audience |
|---|---|---|---|
| `prompts/{task_id}.md` (prompt file) | English | class IDs (`formal`) | LLM classifiers; initial import |
| DB `tasks` row | Czech `description_md` | Czech labels (`formální`) | annotators |

**The DB is authoritative for annotation.** The Czech task prompts and labels were edited in the DB and exist nowhere else.

**Import overwrites.** `POST /api/admin/tasks/import-prompts` (Admin → Import) upserts every prompt file and replaces `name`, `description_md`, `classes`, `multi_choice`, `max_choices` and `enabled`. Running it replaces the Czech DB content with the English prompt files. To change a single task, edit it in Admin → Tasks or `POST /api/admin/tasks`.

The class IDs in the prompt files and in the DB must stay identical, so that LLM output can be compared with human annotations.

## Labels and prompts

- `label_cs`: human-readable Czech words with spaces, no underscores (e.g. `závislý na kontextu`).
- `label_en`: English; the importer derives it from the class ID.
- The task prompt refers to each class by its exact `label_cs` in backticks, in the class list and in the rules. No inflected forms, no „…“ quotes.
- The classification page (`ClassificationPage.vue`) shows `label_cs` on the radio buttons and checkboxes, in the summary panel and in the calibration feedback. `label_en` is shown only in the admin task editor.

Check that every label appears in its task prompt:

```bash
cd backend && python3 - <<'EOF'
import sqlite3, json
c = sqlite3.connect('database.sqlite')
for tid, cls, md in c.execute('select id, classes, description_md from tasks'):
    for k in json.loads(cls):
        if '_' in k['label_cs'] or f"`{k['label_cs']}`" not in md:
            print(tid, k['label_cs'])
EOF
```

## Prompt file format (import)

Parser: `backend/text_classifier/prompt_parser.py`.

- Task ID = file stem.
- Name = the text after `# Task -` / `# Task:`; otherwise the humanized file stem.
- Classes are read from the section headed `# Classes` or `# Possible classes`, up to the next `#` heading. The section heading must use a single `#`.
- Class line: ``- `class_id` — description`` or ``- `class_id` / `label_cs` — description``. If `label_cs` is missing, the class ID is used.
- `multi_choice = true`, `max_choices = 2` if the text contains one of: `one or two class labels`, `optionally choose a second`, `choose up to two`, `select up to two`, `multiple classes`, `multiple options`. Otherwise single choice.
- `enabled = true`; sampling settings get schema defaults.

## Validation

At save (`TaskDefinition`):
- at least one class;
- single choice ⇒ `max_choices = 1`;
- `max_choices ≤ len(classes)`.

At submit (`crud.save_annotations`):
- every selected class ID exists in the task;
- single choice: exactly one class;
- multi choice: from 1 to `max_choices` classes;
- the task is enabled.

## Rules

- Never rename or remove a class ID after annotation has started. Add a new class instead.
- Disable a task rather than delete it.
- Before bulk edits, back up the DB ([operations.md](operations.md#backups)).
