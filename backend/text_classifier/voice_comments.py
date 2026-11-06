"""Voice comments: audio storage, creation and background transcription.

See docs/voice_comments.md.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from text_classifier.config import config
from text_classifier.db_model import AnnotationSession, Task, TranscriptionStatus, VoiceComment

logger = logging.getLogger(__name__)

# Languages an annotator can choose for a recording (ISO 639-1, as the OpenAI API expects).
VOICE_LANGUAGES = ['cs', 'sk']

# Slack for client timer and encoder latency when checking the recording length.
_DURATION_SLACK_MS = 5000

_EXTENSIONS = {
    'audio/webm': 'webm',
    'audio/ogg': 'ogg',
    'audio/mp4': 'mp4',
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'audio/x-wav': 'wav',
}


class VoiceCommentError(Exception):
    """Invalid voice comment upload; `status` is the HTTP status to return."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def audio_root() -> Path:
    return Path(config.VOICE_AUDIO_PATH)


def audio_file(vc: VoiceComment) -> Path:
    return audio_root() / vc.file_path


def _base_mime(mime_type: str) -> str:
    return mime_type.split(';', 1)[0].strip().lower()


async def create_voice_comment(
    db: AsyncSession,
    user_id,
    session_id: uuid.UUID,
    language: str,
    start_ms: int,
    end_ms: int,
    mime_type: str,
    data: bytes,
) -> VoiceComment:
    """Validate and store one recording for a submitted annotation session.

    Writes the audio file, then adds the DB row (the caller commits). At most one
    voice comment per session: a second upload is rejected (no re-recording).
    """
    if language not in VOICE_LANGUAGES:
        raise VoiceCommentError(400, f"Unsupported language '{language}'")
    base_mime = _base_mime(mime_type)
    ext = _EXTENSIONS.get(base_mime)
    if ext is None:
        raise VoiceCommentError(415, f"Unsupported audio type '{mime_type}'")
    if not data:
        raise VoiceCommentError(400, 'Empty recording')
    if len(data) > config.VOICE_MAX_BYTES:
        raise VoiceCommentError(413, 'Recording too large')
    if start_ms < 0 or end_ms < start_ms:
        raise VoiceCommentError(400, 'Invalid recording timestamps')
    if end_ms - start_ms > config.VOICE_MAX_SECONDS * 1000 + _DURATION_SLACK_MS:
        raise VoiceCommentError(400, 'Recording too long')

    session = await db.get(AnnotationSession, session_id)
    if session is None or session.user_id != user_id:
        raise VoiceCommentError(404, 'Annotation session not found')
    existing = (await db.execute(
        select(VoiceComment.id).where(VoiceComment.session_id == session_id)
    )).scalar_one_or_none()
    if existing is not None:
        raise VoiceCommentError(409, 'This annotation session already has a voice comment')

    vc_id = uuid.uuid4()
    rel_path = Path(datetime.utcnow().strftime('%Y-%m')) / f'{vc_id}.{ext}'
    abs_path = audio_root() / rel_path
    await asyncio.to_thread(_write_file, abs_path, data)

    vc = VoiceComment(
        id=vc_id,
        session_id=session_id,
        user_id=user_id,
        text_id=session.text_id,
        language=language,
        file_path=rel_path.as_posix(),
        mime_type=base_mime,
        size_bytes=len(data),
        start_ms=start_ms,
        end_ms=end_ms,
        transcription_status=TranscriptionStatus.pending,
        transcription_attempts=0,
    )
    db.add(vc)
    return vc


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_bytes(data)
    tmp.replace(path)


async def reset_transcription(db: AsyncSession, vc_id: uuid.UUID) -> bool:
    """Queue a voice comment for transcription again (admin retry)."""
    vc = await db.get(VoiceComment, vc_id)
    if vc is None:
        return False
    vc.transcription_status = TranscriptionStatus.pending
    vc.transcription_attempts = 0
    vc.transcription_error = None
    return True


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

@dataclass
class TranscriptResult:
    text: str
    model: str
    segments: list[dict] | None = None


class Transcriber(Protocol):
    async def transcribe(
        self, path: Path, mime_type: str, language: str, prompt: str | None,
    ) -> TranscriptResult: ...


class OpenAITranscriber:
    """Transcribes through the OpenAI audio transcription endpoint."""

    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def transcribe(
        self, path: Path, mime_type: str, language: str, prompt: str | None,
    ) -> TranscriptResult:
        data = await asyncio.to_thread(path.read_bytes)
        kwargs: dict = {
            'model': self._model,
            'file': (path.name, data, mime_type),
            'language': language,
        }
        if prompt:
            kwargs['prompt'] = prompt
        # Only whisper-1 returns segment timestamps (verbose_json).
        if self._model == 'whisper-1':
            kwargs['response_format'] = 'verbose_json'
            kwargs['timestamp_granularities'] = ['segment']
        resp = await self._client.audio.transcriptions.create(**kwargs)
        segments = None
        raw_segments = getattr(resp, 'segments', None)
        if raw_segments:
            segments = [
                {'start': float(s.start), 'end': float(s.end), 'text': s.text}
                for s in raw_segments
            ]
        return TranscriptResult(text=resp.text, model=self._model, segments=segments)


def default_transcriber() -> Transcriber | None:
    """The configured transcriber, or None when transcription is off or has no API key."""
    if not config.TRANSCRIBE_ENABLED or not config.OPENAI_API_KEY:
        return None
    return OpenAITranscriber(config.OPENAI_API_KEY, config.OPENAI_TRANSCRIBE_MODEL)


async def _vocabulary_prompt(db: AsyncSession, session_id: uuid.UUID) -> str | None:
    """Task names and class labels of the session, to help spell domain terms."""
    session = await db.get(AnnotationSession, session_id)
    if session is None or not session.task_ids:
        return None
    tasks = (await db.execute(select(Task).where(Task.id.in_(session.task_ids)))).scalars().all()
    words: list[str] = []
    for t in tasks:
        words.append(t.name)
        words.extend(c.get('label_cs', '') for c in t.classes)
    prompt = ', '.join(w for w in words if w)
    return prompt[:800] or None


async def transcribe_pending(
    db: AsyncSession, transcriber: Transcriber, limit: int = 20,
) -> int:
    """Transcribe pending voice comments; commits after each one. Returns the number processed."""
    rows = (await db.execute(
        select(VoiceComment)
        .where(VoiceComment.transcription_status == TranscriptionStatus.pending)
        .where(VoiceComment.transcription_attempts < config.TRANSCRIBE_MAX_ATTEMPTS)
        .order_by(VoiceComment.created_at)
        .limit(limit)
    )).scalars().all()
    for vc in rows:
        vc.transcription_attempts += 1
        try:
            prompt = await _vocabulary_prompt(db, vc.session_id)
            result = await transcriber.transcribe(audio_file(vc), vc.mime_type, vc.language, prompt)
        except Exception as exc:  # noqa: BLE001 - any provider/file error is recorded and retried
            logger.warning('[transcription] %s failed (attempt %d): %s', vc.id, vc.transcription_attempts, exc)
            vc.transcription_error = str(exc)[:2000]
            if vc.transcription_attempts >= config.TRANSCRIBE_MAX_ATTEMPTS:
                vc.transcription_status = TranscriptionStatus.failed
        else:
            vc.transcript = result.text
            vc.transcript_segments = result.segments
            vc.transcription_model = result.model
            vc.transcription_error = None
            vc.transcription_status = TranscriptionStatus.done
            vc.transcribed_at = datetime.utcnow()
        await db.commit()
    return len(rows)


# Set by the upload route so the loop runs right away instead of waiting for the interval.
transcription_wakeup = asyncio.Event()


async def transcription_loop(session_maker, transcriber: Transcriber | None) -> None:
    """Background loop: transcribe pending voice comments (single worker)."""
    if transcriber is None:
        logger.warning('[transcription] disabled (TRANSCRIBE_ENABLED=false or no OPENAI_API_KEY); voice comments stay pending')
        return
    while True:
        try:
            async with session_maker() as db:
                await transcribe_pending(db, transcriber)
        except Exception as exc:  # noqa: BLE001
            logger.error('[transcription] loop error: %s', exc)
        try:
            await asyncio.wait_for(transcription_wakeup.wait(), timeout=config.TRANSCRIBE_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass
        transcription_wakeup.clear()
