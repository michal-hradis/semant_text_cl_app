"""Tests for the "fill up to target" text sampler and soft reservations."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

from text_classifier.base_objects import TaskClass, TaskDefinition
from text_classifier.crud import coverage_stats, get_next_text, upsert_task, upsert_text
from text_classifier.database import Base
from text_classifier.db_model import Annotation, AnnotationType
from text_classifier.reservations import ReservationStore


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _run_with_db(setup_and_check):
    async def _run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            await setup_and_check(db)
        await engine.dispose()
    asyncio.run(_run())


async def _add_task(db, task_id, target=4):
    await upsert_task(db, TaskDefinition(
        id=task_id, name=task_id, description_md='d', multi_choice=False, max_choices=1,
        enabled=True, classes=[TaskClass(id='a', label_en='A', label_cs='a')],
        target_coverage=target,
    ))


async def _add_texts(db, *ids):
    for i in ids:
        await upsert_text(db, i, f'text {i}', 'eng', {'id': i})


def _annotate(db, text_id, task_id, user_id=None, ann_type=AnnotationType.user):
    now = datetime.utcnow()
    db.add(Annotation(
        user_id=user_id or uuid4(), text_id=text_id, task_id=task_id, selected_classes=['a'],
        start_time=now, end_time=now, annotation_type=ann_type,
    ))


def _store():
    return ReservationStore(ttl_seconds=100, clock=FakeClock())


def test_prefers_text_closest_to_target():
    async def check(db):
        await _add_task(db, 'A')
        await _add_texts(db, 'fresh', 'almost')
        for _ in range(3):
            _annotate(db, 'almost', 'A')
        await db.commit()
        for _ in range(10):
            text, _ = await get_next_text(db, uuid4(), ['A'], store=_store())
            assert text.id == 'almost'
    _run_with_db(check)


def test_saturated_text_not_picked():
    async def check(db):
        await _add_task(db, 'A', target=2)
        await _add_texts(db, 'full', 'empty')
        for _ in range(2):
            _annotate(db, 'full', 'A')
        await db.commit()
        for _ in range(10):
            text, _ = await get_next_text(db, uuid4(), ['A'], store=_store())
            assert text.id == 'empty'
    _run_with_db(check)


def test_prefers_text_useful_for_more_selected_tasks():
    async def check(db):
        await _add_task(db, 'A')
        await _add_task(db, 'B')
        await _add_texts(db, 'one_task', 'two_tasks')
        # one_task: A needs annotations (1 done), B already full.
        _annotate(db, 'one_task', 'A')
        for _ in range(4):
            _annotate(db, 'one_task', 'B')
        # two_tasks: both A and B have 1 annotation.
        _annotate(db, 'two_tasks', 'A')
        _annotate(db, 'two_tasks', 'B')
        await db.commit()
        for _ in range(10):
            text, _ = await get_next_text(db, uuid4(), ['A', 'B'], store=_store())
            assert text.id == 'two_tasks'
        # A user with only task A sees both texts as equal (score 2 each).
        seen = {(await get_next_text(db, uuid4(), ['A'], store=_store()))[0].id for _ in range(40)}
        assert seen == {'one_task', 'two_tasks'}
    _run_with_db(check)


def test_users_own_annotations_do_not_count():
    async def check(db):
        await _add_task(db, 'A')
        await _add_texts(db, 'mine', 'other')
        me = uuid4()
        _annotate(db, 'mine', 'A', user_id=me)
        _annotate(db, 'mine', 'A')
        _annotate(db, 'other', 'A')
        await db.commit()
        for _ in range(10):
            text, _ = await get_next_text(db, me, ['A'], store=_store())
            assert text.id == 'other'
    _run_with_db(check)


def test_non_user_annotations_are_ignored():
    async def check(db):
        await _add_task(db, 'A', target=1)
        await _add_texts(db, 'gt_only', 'user_done')
        _annotate(db, 'gt_only', 'A', ann_type=AnnotationType.ground_truth)
        _annotate(db, 'gt_only', 'A', ann_type=AnnotationType.llm)
        _annotate(db, 'user_done', 'A')
        await db.commit()
        text, _ = await get_next_text(db, uuid4(), ['A'], store=_store())
        assert text.id == 'gt_only'
    _run_with_db(check)


def test_reservation_counts_as_pending_and_expires():
    async def check(db):
        await _add_task(db, 'A', target=1)
        await _add_texts(db, 't1', 't2')
        await db.commit()
        clock = FakeClock()
        store = ReservationStore(ttl_seconds=100, clock=clock)
        u1, u2 = uuid4(), uuid4()
        first, _ = await get_next_text(db, u1, ['A'], store=store)
        second, _ = await get_next_text(db, u2, ['A'], store=store)
        assert first.id != second.id, 'reserved text should be considered full'

        # After expiry, the reservation no longer counts.
        clock.t = 1000
        store.release(u2)
        assert store.pending() == {}
    _run_with_db(check)


def test_new_request_replaces_reservation_and_release_clears():
    store = _store()
    u = uuid4()
    store.reserve(u, 't1', ['A'])
    store.reserve(u, 't2', ['A', 'B'])
    assert set(store.pending()) == {('t2', 'A'), ('t2', 'B')}
    assert store.pending(exclude_user=u) == {}
    store.release(u)
    assert store.pending() == {}


def test_fallback_when_everything_saturated():
    async def check(db):
        await _add_task(db, 'A', target=1)
        await _add_texts(db, 'seen', 'unseen')
        me = uuid4()
        _annotate(db, 'seen', 'A', user_id=me)
        _annotate(db, 'unseen', 'A')
        await db.commit()
        for _ in range(10):
            text, _ = await get_next_text(db, me, ['A'], store=_store())
            assert text.id == 'unseen'
        # Once the user has seen everything, a repeat is still served.
        _annotate(db, 'unseen', 'A', user_id=me)
        await db.commit()
        text, _ = await get_next_text(db, me, ['A'], store=_store())
        assert text is not None
    _run_with_db(check)


def test_coverage_stats():
    async def check(db):
        await _add_task(db, 'A', target=2)
        await _add_texts(db, 'full', 'half', 'none')
        _annotate(db, 'full', 'A')
        _annotate(db, 'full', 'A')
        _annotate(db, 'half', 'A')
        await db.commit()
        [row] = await coverage_stats(db)
        assert row['target'] == 2
        assert row['active_texts'] == 3
        assert (row['complete_texts'], row['partial_texts'], row['untouched_texts']) == (1, 1, 1)
        assert row['missing_annotations'] == 3
    _run_with_db(check)
