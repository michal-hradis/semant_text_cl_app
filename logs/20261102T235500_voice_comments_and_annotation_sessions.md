# Voice comments and annotation sessions

## What changed

- **Annotation sessions** (`annotation_sessions` table): every submit can now carry `session = {id, client_started_at, events[]}`. Events are timestamped annotator actions (text/task shown, class selected/deselected, prompt opened/closed, recording start/stop/discard/max length, page hidden/visible, submit) on a per-text monotonic clock (`t_ms`). Stored with the IDs of the created annotations.
- **Voice comments** (`voice_comments` table, audio in `VOICE_AUDIO_PATH`): one recording per annotation session, uploaded with `POST /api/voice-comments` after a successful submit. Max length `VOICE_MAX_SECONDS` (default 300 s). A second upload for the same session → 409.
- **Transcription**: background loop in `voice_comments.py` calls OpenAI (`OPENAI_TRANSCRIBE_MODEL`, default `gpt-4o-transcribe`) with the chosen language (cs/sk) and a vocabulary prompt from the session's task names and class labels. Retries up to `TRANSCRIBE_MAX_ATTEMPTS`; admin can re-queue.
- **Annotation UI**: the only new control is a Recording on/off button (red and pulsing with the elapsed time while recording) with a cs/sk language picker. A basic one-time consent dialog. Class changes and the prompt toggle are now logged as events.
- **Admin**: Texts → annotations dialog → "Sessions & voice comments" tab with audio, transcript, status and an event timeline where clicking a time seeks the audio.
- New dependencies: `openai`, `python-multipart` (explicit).
- Docs: new `docs/voice_comments.md`; glossary, data model, API reference, code map, operations, architecture, admin guide updated. `frontend/openapi.json` regenerated (additions only).

## Decisions

- **One recording per text, no re-recording**: the recording captures the annotator's inner monologue while deciding; editing or re-recording would change its meaning. Turning recording off discards the current text's audio and blocks recording for that text; it resumes from the next text if turned back on.
- **Upload after submit, separately**: annotations never depend on the upload; a failed upload loses only the audio. The session must exist (and belong to the uploader) before a voice comment can be attached.
- **Client-generated session ID and session clock**: event times and recording start/end share one monotonic client clock, so `event.t_ms − start_ms` gives the audio position without clock-skew issues.
- **Session → annotations link via `annotation_ids` JSON** instead of a new `annotations.session_id` column: only new tables, so `create_all` handles existing DBs and no manual `ALTER TABLE` is needed.
- **Events are recorded always**, not only while recording, so timing data exists for all new submits.
- **Audio on disk, metadata in DB**; files are written via a temporary `.part` file and renamed.
- **Language picker is frontend-only state** (localStorage) and is sent with each upload; stored per voice comment.
- **Segment timestamps** only with `whisper-1`; the default model gives better Czech/Slovak text without timestamps. Event-to-audio mapping works regardless, via the session clock.
- **Consent** stored in localStorage only (internal use, per request).

## Not verified

- The recording flow was not tested in a real browser with a microphone; backend and build were verified (`pytest`, `quasar build`, eslint).

## Deployment (2026-11-03)

- `config.py` now also reads `backend/.env` (gitignored); `OPENAI_API_KEY` is stored there, not in source. Key checked against the OpenAI API (`gpt-4o-transcribe` accessible).
- New dependencies installed into `backend/env`; frontend rebuilt and copied to `backend/static/` (previous build kept in `backend/db.bak/static_20261103T095049`, DB backup `db.bak/database_20261103T095049_pre_voice_deploy.sqlite`). The running `run.py` (reload mode) picked up the change.
