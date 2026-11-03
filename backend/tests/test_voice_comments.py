"""Tests for annotation sessions, voice comment upload and background transcription."""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

from text_classifier import voice_comments
from text_classifier.base_objects import (
    AnnotationSessionSubmit, AnnotationSubmit, InteractionEvent, TaskAnnotation, TaskClass, TaskDefinition,
)
from text_classifier.config import config
from text_classifier.crud import get_text_sessions, save_annotations, upsert_task, upsert_text
from text_classifier.database import Base, get_async_session
from text_classifier.db_model import AnnotationSession, Task, TranscriptionStatus, VoiceComment
from text_classifier.routes import admin_route, api_route
from text_classifier.users import current_active_user
from text_classifier.voice_comments import (
    TranscriptResult, VoiceCommentError, create_voice_comment, reset_transcription, transcribe_pending,
)

AUDIO = b'\x1aE\xdf\xa3fake-webm-bytes'


@pytest.fixture(autouse=True)
def audio_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'VOICE_AUDIO_PATH', str(tmp_path / 'audio'))
    return tmp_path / 'audio'


def _run(fn):
    async def _inner():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await fn(Session)
        finally:
            await engine.dispose()
    asyncio.run(_inner())


async def _setup(db):
    await upsert_task(db, TaskDefinition(
        id='style', name='Styl', description_md='d', multi_choice=False, max_choices=1, enabled=True,
        classes=[TaskClass(id='formal', label_en='Formal', label_cs='formální'),
                 TaskClass(id='informal', label_en='Informal', label_cs='neformální')],
    ))
    await upsert_text(db, 't1', 'hello', 'ces', {'id': 't1'})
    await db.commit()


def _payload(session_id=None, events=None):
    now = datetime.now(timezone.utc)
    session = None
    if session_id is not None:
        session = AnnotationSessionSubmit(id=session_id, client_started_at=now, events=events or [])
    return AnnotationSubmit(
        text_id='t1',
        annotations=[TaskAnnotation(task_id='style', selected_classes=['formal'], start_time=now, end_time=now)],
        session=session,
    )


async def _submit(db, user_id, session_id, events=None):
    tasks_map = {'style': await db.get(Task, 'style')}
    await save_annotations(db, user_id, _payload(session_id, events), tasks_map)
    await db.commit()


class FakeTranscriber:
    def __init__(self, fail_times=0):
        self.fail_times = fail_times
        self.calls = []

    async def transcribe(self, path, mime_type, language, prompt):
        self.calls.append((path, mime_type, language, prompt))
        if len(self.calls) <= self.fail_times:
            raise RuntimeError('provider down')
        return TranscriptResult(text='myslím, že je to formální', model='fake',
                                segments=[{'start': 0.0, 'end': 1.5, 'text': 'myslím'}])


# ---------------------------------------------------------------------------
# Annotation sessions
# ---------------------------------------------------------------------------

def test_submit_with_session_stores_events_and_annotation_ids():
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            events = [
                InteractionEvent(type='text_shown', t_ms=0),
                InteractionEvent(type='task_shown', t_ms=5, task_id='style'),
                InteractionEvent(type='class_selected', t_ms=1200, task_id='style', class_id='formal'),
                InteractionEvent(type='submitted', t_ms=2000),
            ]
            await _submit(db, uid, sid, events)
            s = await db.get(AnnotationSession, sid)
            assert s.user_id == uid and s.text_id == 't1' and s.task_ids == ['style']
            assert len(s.annotation_ids) == 1
            assert s.events[2] == {'type': 'class_selected', 't_ms': 1200, 'task_id': 'style', 'class_id': 'formal'}
            assert s.client_started_at.tzinfo is None
    _run(check)


def test_submit_without_session_still_works():
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            await _submit(db, uuid4(), None)
            assert (await db.execute(select(AnnotationSession))).first() is None
    _run(check)


def test_duplicate_session_id_is_rejected():
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            await _submit(db, uid, sid)
            with pytest.raises(ValueError):
                await _submit(db, uid, sid)
    _run(check)


# ---------------------------------------------------------------------------
# Voice comment creation
# ---------------------------------------------------------------------------

def test_create_voice_comment_writes_file_and_row(audio_dir):
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            await _submit(db, uid, sid)
            vc = await create_voice_comment(db, uid, sid, 'sk', 100, 4100, 'audio/webm;codecs=opus', AUDIO)
            await db.commit()
            assert vc.mime_type == 'audio/webm'
            assert vc.text_id == 't1'
            assert vc.transcription_status == TranscriptionStatus.pending
            assert (audio_dir / vc.file_path).read_bytes() == AUDIO
            assert vc.file_path.endswith('.webm')
    _run(check)


def test_second_recording_for_same_session_is_rejected():
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            await _submit(db, uid, sid)
            await create_voice_comment(db, uid, sid, 'cs', 0, 1000, 'audio/webm', AUDIO)
            await db.commit()
            with pytest.raises(VoiceCommentError) as e:
                await create_voice_comment(db, uid, sid, 'cs', 0, 1000, 'audio/webm', AUDIO)
            assert e.value.status == 409
    _run(check)


@pytest.mark.parametrize('kwargs,status', [
    ({'user': 'other'}, 404),
    ({'session': 'missing'}, 404),
    ({'language': 'en'}, 400),
    ({'mime': 'text/plain'}, 415),
    ({'data': b''}, 400),
    ({'end_ms': 10_000_000}, 400),
    ({'start_ms': 500, 'end_ms': 100}, 400),
])
def test_invalid_voice_comment_uploads(kwargs, status):
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            await _submit(db, uid, sid)
            with pytest.raises(VoiceCommentError) as e:
                await create_voice_comment(
                    db,
                    uuid4() if kwargs.get('user') == 'other' else uid,
                    uuid4() if kwargs.get('session') == 'missing' else sid,
                    kwargs.get('language', 'cs'),
                    kwargs.get('start_ms', 0),
                    kwargs.get('end_ms', 1000),
                    kwargs.get('mime', 'audio/webm'),
                    kwargs.get('data', AUDIO),
                )
            assert e.value.status == status
    _run(check)


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def test_transcribe_pending_stores_transcript_and_uses_vocabulary():
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            await _submit(db, uid, sid)
            vc = await create_voice_comment(db, uid, sid, 'cs', 0, 1000, 'audio/webm', AUDIO)
            await db.commit()
            fake = FakeTranscriber()
            assert await transcribe_pending(db, fake) == 1
            await db.refresh(vc)
            assert vc.transcription_status == TranscriptionStatus.done
            assert vc.transcript == 'myslím, že je to formální'
            assert vc.transcript_segments[0]['text'] == 'myslím'
            assert vc.transcription_model == 'fake'
            _, mime, lang, prompt = fake.calls[0]
            assert (mime, lang) == ('audio/webm', 'cs')
            assert 'Styl' in prompt and 'neformální' in prompt
            # Nothing left to do
            assert await transcribe_pending(db, fake) == 0
    _run(check)


def test_transcription_retries_then_fails_and_can_be_reset(monkeypatch):
    monkeypatch.setattr(config, 'TRANSCRIBE_MAX_ATTEMPTS', 2)

    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid, sid = uuid4(), uuid4()
            await _submit(db, uid, sid)
            vc = await create_voice_comment(db, uid, sid, 'cs', 0, 1000, 'audio/webm', AUDIO)
            await db.commit()
            fake = FakeTranscriber(fail_times=2)
            await transcribe_pending(db, fake)
            await db.refresh(vc)
            assert vc.transcription_status == TranscriptionStatus.pending
            assert vc.transcription_error == 'provider down'
            await transcribe_pending(db, fake)
            await db.refresh(vc)
            assert vc.transcription_status == TranscriptionStatus.failed
            assert vc.transcription_attempts == 2
            assert await transcribe_pending(db, fake) == 0

            assert await reset_transcription(db, vc.id)
            await db.commit()
            await transcribe_pending(db, fake)
            await db.refresh(vc)
            assert vc.transcription_status == TranscriptionStatus.done
            assert vc.transcription_error is None
    _run(check)


# ---------------------------------------------------------------------------
# Admin view
# ---------------------------------------------------------------------------

def test_get_text_sessions_includes_annotations_and_voice_comment():
    async def check(Session):
        async with Session() as db:
            await _setup(db)
            uid = uuid4()
            sid_with, sid_without = uuid4(), uuid4()
            await _submit(db, uid, sid_with, [InteractionEvent(type='text_shown', t_ms=0)])
            await _submit(db, uid, sid_without)
            await create_voice_comment(db, uid, sid_with, 'cs', 50, 2050, 'audio/mp4', AUDIO)
            await db.commit()
            sessions = {s['session_id']: s for s in await get_text_sessions(db, 't1')}
            assert set(sessions) == {str(sid_with), str(sid_without)}
            s = sessions[str(sid_with)]
            assert s['annotations'][0]['selected_classes'] == ['formal']
            assert s['events'] == [{'type': 'text_shown', 't_ms': 0}]
            assert s['voice_comment']['start_ms'] == 50
            assert s['voice_comment']['mime_type'] == 'audio/mp4'
            assert sessions[str(sid_without)]['voice_comment'] is None
    _run(check)


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

def test_upload_and_admin_routes(audio_dir):
    async def check(Session):
        async with Session() as db:
            await _setup(db)

        annotator = SimpleNamespace(id=uuid4(), is_superuser=False)
        admin = SimpleNamespace(id=uuid4(), is_superuser=True)
        current = {'user': annotator}

        app = FastAPI()
        app.include_router(api_route, prefix='/api')
        app.include_router(admin_route, prefix='/api/admin')

        async def _session():
            async with Session() as s:
                yield s
        app.dependency_overrides[get_async_session] = _session
        app.dependency_overrides[current_active_user] = lambda: current['user']

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
            r = await client.get('/api/voice-comments/config')
            assert r.json() == {'enabled': True, 'max_seconds': config.VOICE_MAX_SECONDS, 'languages': ['cs', 'sk']}

            sid = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()
            r = await client.post('/api/annotations', json={
                'text_id': 't1',
                'annotations': [{'task_id': 'style', 'selected_classes': ['formal'], 'start_time': now, 'end_time': now}],
                'session': {'id': sid, 'client_started_at': now,
                            'events': [{'type': 'text_shown', 't_ms': 0}, {'type': 'submitted', 't_ms': 900}]},
            })
            assert r.status_code == 200, r.text

            form = {'session_id': sid, 'language': 'cs', 'start_ms': '10', 'end_ms': '890'}
            files = {'audio': ('rec.webm', AUDIO, 'audio/webm;codecs=opus')}
            r = await client.post('/api/voice-comments', data=form, files=files)
            assert r.status_code == 201, r.text
            vc_id = r.json()['id']
            assert r.json()['transcription_status'] == 'pending'

            r = await client.post('/api/voice-comments', data=form, files=files)
            assert r.status_code == 409

            # Annotators cannot use admin routes
            assert (await client.get('/api/admin/texts/t1/sessions')).status_code == 403
            assert (await client.get(f'/api/admin/voice-comments/{vc_id}/audio')).status_code == 403

            current['user'] = admin
            r = await client.get('/api/admin/texts/t1/sessions')
            assert r.status_code == 200
            [entry] = r.json()
            assert entry['voice_comment']['id'] == vc_id
            assert entry['events'][1] == {'type': 'submitted', 't_ms': 900, 'task_id': None, 'class_id': None}

            r = await client.get(f'/api/admin/voice-comments/{vc_id}/audio')
            assert r.status_code == 200
            assert r.content == AUDIO
            assert r.headers['content-type'].startswith('audio/webm')

            r = await client.post(f'/api/admin/voice-comments/{vc_id}/retranscribe')
            assert r.status_code == 204
            assert (await client.post(f'/api/admin/voice-comments/{uuid4()}/retranscribe')).status_code == 404

    _run(check)
