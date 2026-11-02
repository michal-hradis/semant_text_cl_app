# UI Improvements

All planned improvements have been implemented as of 2026-05-31.

## Completed

- **Global layout** — max-width 960 px centred container, icon navbar, display name shown.
- **User display name** — optional field on registration; shown in navbar and leaderboards.
- **TaskSelectionDialog** — full-screen dialog with markdown descriptions, pre-filled selection, max-6 limit; replaces the old TaskSelectionPage.
- **ClassificationPage** — one task at a time, progress bar, strict navigation, always-visible summary panel with restricted jump (answered tasks + next), collapsible task description, per-class `(i)` tooltip, per-task start-time tracking.
- **LeaderboardPage** — own stats, overall leaderboard (weekly/all-time tabs), global stats table, per-task leaderboards loaded lazily.
- **AdminPage** — three tabs: Tasks (table with create/edit/delete/toggle), Import (prompts/*.md), Texts (file upload, paginated browse with search, suspend/unsuspend).
- **TaskClass.description** — parser extracts description from prompt markdown (text after `—`); shown as tooltip; editable in AdminPage task editor.
- **Backend** — `display_name` on User, `suspended` on TextItem, new endpoints for global stats, overall leaderboard, text listing/patching.

## Notes

- SQLite `create_all` does not alter existing tables; delete the dev database after pulling to pick up `display_name` and `suspended` columns.
- Re-import tasks via Admin → Import to populate per-class descriptions from the prompt files.
