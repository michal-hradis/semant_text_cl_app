# Voice Comments and Annotation Sessions

Annotators can think aloud while they annotate. The recording captures how they decide, so it is never edited or re-recorded. Terms: [glossary.md](glossary.md).

Source: `backend/text_classifier/voice_comments.py`, `crud.save_annotations` / `crud.get_text_sessions`, `frontend/src/composables/useVoiceRecorder.ts`, `frontend/src/pages/ClassificationPage.vue`, `frontend/src/components/AnnotationSessionsView.vue`.

## Annotation session

One annotation session = one text shown to one annotator, from display until submit.

- The client creates the session ID (UUID) when the text is shown and starts a **session clock** (`performance.now()`, monotonic). `client_started_at` is the client wall-clock time at that moment.
- Every interaction event is stored as `{type, t_ms, task_id?, class_id?}`; `t_ms` = ms on the session clock.
- On submit the session goes with the annotations in `AnnotationSubmit.session`. The backend stores it in `annotation_sessions` with the IDs of the annotations it created. A session ID can be submitted only once.
- Events are recorded whether or not recording is on. A text that is left without submitting (task change, reload) leaves no session.

| Event `type` | Extra fields | When |
|---|---|---|
| `text_shown` | | Session start (`t_ms` = 0). |
| `task_shown` | `task_id` | A task step is displayed (first task, Next, Back, summary click). |
| `class_selected`, `class_deselected` | `task_id`, `class_id` | A class is checked or unchecked. Switching a single-choice answer logs only `class_selected`. |
| `description_shown`, `description_hidden` | `task_id` | Task prompt opened or closed. |
| `recording_started` | | The recorder actually started (after microphone access). |
| `recording_stopped` | | Recording ended at submit. |
| `recording_max_reached` | | Recording stopped at `VOICE_MAX_SECONDS`; the audio so far is kept. |
| `recording_discarded` | | The annotator turned recording off; this text's audio is dropped. |
| `page_hidden`, `page_visible` | | Browser tab hidden or shown again. |
| `submitted`, `submit_failed` | | Submit clicked; failure is logged if the request fails (a retry logs `submitted` again). |

## Voice comment

At most one voice comment per annotation session (that is, per text shown).

- **Recording on/off** is the only control in the annotation UI, next to a cs/sk language picker. The button turns red and pulses while recording and shows the elapsed time. Both choices persist in `localStorage` (`voice_recording_enabled`, `voice_language`).
- When recording is on, it starts as soon as a text is shown and stops at submit. Turning it on mid-text starts it immediately.
- Turning it off discards the current recording, which is never uploaded. Recording stays off for later texts until turned on again. A discarded text is not recorded again, even if recording is turned back on (no re-recording).
- After a successful submit the client uploads the audio (`POST /api/voice-comments`) with `start_ms` / `end_ms` on the session clock. If the upload fails, the annotation is kept and the recording is lost.
- **Mapping actions to audio**: position in the recording = `event.t_ms − voice_comment.start_ms`, valid while `start_ms ≤ t_ms ≤ end_ms`. Transcript segments (if any) are in seconds from the recording start. The admin timeline merges both.
- **Capture**: the microphone is opened with echo cancellation, noise suppression and auto gain control off (raw signal; the call-oriented defaults cut quiet speech out). The recorder runs without a timeslice and yields one blob at stop.
- **Consent**: the first time recording is turned on, a short dialog explains storage, possible later OpenAI transcription and admin-only access. Acceptance is stored in `localStorage` (`voice_consent_v1`) only.

Browser requirements: `MediaRecorder` and microphone access, which needs HTTPS (or localhost). Chrome and Firefox record `audio/webm` (Opus), Safari `audio/mp4`. If unsupported or `VOICE_COMMENTS_ENABLED=false`, the button is hidden.

## Storage

- Audio files: `VOICE_AUDIO_PATH/{YYYY-MM}/{voice_comment_id}.{ext}`. The DB row (`voice_comments`) holds the relative path, MIME type, size, `start_ms`, `end_ms`, language and the transcription fields.
- Upload checks: session exists and belongs to the user (404); no voice comment for it yet (409); language in `cs`, `sk` (400); audio type webm/ogg/mp4/mpeg/wav (415); size ≤ `VOICE_MAX_BYTES` (413); `end_ms − start_ms` ≤ `VOICE_MAX_SECONDS` + 5 s (400).
- Back up `VOICE_AUDIO_PATH` together with the DB ([operations.md](operations.md#backups)).

## Transcription

- **Off by default** (`TRANSCRIBE_ENABLED=false`) until recordings are validated: audio is stored and voice comments stay `pending`. Set `TRANSCRIBE_ENABLED=true` (plus `OPENAI_API_KEY`) to transcribe; the backlog of `pending` recordings is then processed.
- Background loop (`voice_comments.transcription_loop`, started in `main.lifespan`): runs every `TRANSCRIBE_INTERVAL_SECONDS`, and right after each upload or retry.
- Picks `pending` voice comments with `transcription_attempts < TRANSCRIBE_MAX_ATTEMPTS`, oldest first, and calls OpenAI `audio.transcriptions` with model `OPENAI_TRANSCRIBE_MODEL`, the chosen `language` and a prompt made of the session's task names and Czech class labels (spelling hint, ≤ 800 chars).
- Success → `done`, `transcript`, `transcription_model`, `transcribed_at`. Failure → `transcription_error`; the status becomes `failed` after the last attempt.
- `transcript_segments` (`[{start, end, text}]`, seconds) is filled only with `whisper-1`, the only model that returns segment timestamps. The default `gpt-4o-transcribe` returns plain text.
- Without `TRANSCRIBE_ENABLED` or `OPENAI_API_KEY` the loop does not run and voice comments stay `pending`. Admin → **Transcribe again** (`POST /api/admin/voice-comments/{id}/retranscribe`) resets a voice comment to `pending` with 0 attempts.
- Single worker only, like reservations.

## Admin view

Admin → Texts → a text's annotations → **Sessions & voice comments** tab: one row per session with its annotations, the audio player (loaded on demand), the transcript and status, and a timeline of events (and transcript segments). Clicking an audio time seeks the player. MediaRecorder WebM files have no duration or seek index; on load the player seeks past the end once so the browser computes the duration, which makes later seeks exact.
