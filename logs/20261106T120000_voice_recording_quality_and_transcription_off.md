# Voice recording quality fix; transcription off by default

## Problem
Recordings sounded choppy ("drops in and out") and seemed scrambled or out of order.

## Findings
The stored production file (Chrome, WebM/Opus, 71.6 s) is intact: 1194 packets of 60 ms with continuous timestamps, no gaps or reordering, and it decodes without errors. The duration matches `end_ms − start_ms`. So upload and storage were fine. Two causes remain:

1. **Capture**: `getUserMedia({audio: true})` turns on Chrome's call processing (noise suppression, echo cancellation, auto gain). The decoded signal drops to near-digital silence (RMS ≈ 1/32768) between words, which is noise-suppression gating. It cuts quiet or trailing speech, and the transcript covered only part of what was said.
2. **Playback**: MediaRecorder WebM has no duration or cues (`Duration: N/A`). The admin `<audio>` player cannot seek it reliably, so clicking timeline times jumped to wrong places, which sounds like out-of-order audio.

## Changes
- `useVoiceRecorder.ts`: open the mic with `echoCancellation`, `noiseSuppression`, `autoGainControl` off and mono. Drop the 1 s timeslice in `MediaRecorder.start()`, so the recorder emits one blob at stop. Chunked output was not shown to be broken; this just removes a moving part.
- `AnnotationSessionsView.vue`: on `loadedmetadata`, if the duration is not finite, seek to 1e101 once so the browser computes the duration, then go back (or to a pending timeline seek). Preload `auto`.
- Transcription: new `TRANSCRIBE_ENABLED` (default `false`). When it is false, `default_transcriber()` returns None and the loop does not run. Uploads stay `pending` and get transcribed once it is turned on. Consent text now says "may later be sent to OpenAI".
- Docs: voice_comments.md, operations.md, architecture.md.

## Notes
- Recordings already stored keep the processed audio. Playback seeking is fixed for them too.
- The pre-existing failure `test_bulk_gt_annotations_and_calibration_path` is unrelated.
