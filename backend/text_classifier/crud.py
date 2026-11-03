from __future__ import annotations

import math
import random
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from text_classifier import base_objects
from text_classifier.database import User
from text_classifier.db_model import (
    Annotation, AnnotationSession, AnnotationType, Task, TextItem, UserReliability, VoiceComment,
)
from text_classifier.reservations import ReservationStore, reservations

import logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _display_name(dn: str | None, user_id) -> str:
    return dn if dn else str(user_id)[:8]


def _scarcity_multiplier(avg_coverage: float, target_coverage: int) -> float:
    """Returns a value in [1.0, 2.0]: higher when coverage is below target."""
    return 1.0 + max(0.0, 1.0 - avg_coverage / max(target_coverage, 1))


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

_TASK_READONLY = {"current_multiplier"}


async def upsert_task(db: AsyncSession, task: base_objects.TaskDefinition) -> None:
    db_task = await db.get(Task, task.id)
    payload = {k: v for k, v in task.model_dump().items() if k not in _TASK_READONLY}
    if db_task is None:
        db.add(Task(**payload))
    else:
        for k, v in payload.items():
            setattr(db_task, k, v)


async def set_task_state(db: AsyncSession, task_id: str, patch: base_objects.TaskStatePatch) -> bool:
    task = await db.get(Task, task_id)
    if task is None:
        return False
    if patch.deleted:
        await db.execute(delete(Task).where(Task.id == task_id))
        return True
    if patch.enabled is not None:
        task.enabled = patch.enabled
    return True


async def list_tasks(db: AsyncSession, *, enabled_only: bool = False) -> list[Task]:
    query = select(Task).order_by(Task.id)
    if enabled_only:
        query = query.where(Task.enabled.is_(True))
    rows = await db.execute(query)
    return list(rows.scalars().all())


async def list_enabled_tasks(db: AsyncSession) -> list[dict]:
    """Return enabled tasks serialised as dicts, with current_multiplier filled in."""
    tasks = await list_tasks(db, enabled_only=True)
    total_texts = (await db.execute(
        select(func.count()).select_from(TextItem).where(TextItem.suspended.is_(False))
    )).scalar_one()
    result = []
    for t in tasks:
        d = {
            'id': t.id, 'name': t.name, 'description_md': t.description_md,
            'multi_choice': t.multi_choice, 'max_choices': t.max_choices, 'enabled': t.enabled,
            'classes': t.classes,
            'calib_ratio_initial': t.calib_ratio_initial, 'calib_initial_count': t.calib_initial_count,
            'calib_ratio_ongoing': t.calib_ratio_ongoing, 'repeat_probability': t.repeat_probability,
            'target_coverage': t.target_coverage,
            'current_multiplier': None,
        }
        if total_texts > 0:
            total_ann = (await db.execute(
                select(func.count()).select_from(Annotation)
                .where(Annotation.task_id == t.id, Annotation.annotation_type == AnnotationType.user)
            )).scalar_one()
            avg_coverage = total_ann / total_texts
            d['current_multiplier'] = _scarcity_multiplier(avg_coverage, t.target_coverage)
        result.append(d)
    return result


async def get_task_multiplier(db: AsyncSession, task_id: str, target_coverage: int) -> float:
    total_texts = (await db.execute(
        select(func.count()).select_from(TextItem).where(TextItem.suspended.is_(False))
    )).scalar_one()
    if total_texts == 0:
        return 1.0
    total_ann = (await db.execute(
        select(func.count()).select_from(Annotation)
        .where(Annotation.task_id == task_id, Annotation.annotation_type == AnnotationType.user)
    )).scalar_one()
    avg_coverage = total_ann / total_texts
    return _scarcity_multiplier(avg_coverage, target_coverage)


# ---------------------------------------------------------------------------
# Text CRUD
# ---------------------------------------------------------------------------

async def upsert_text(db: AsyncSession, text_id: str, text: str, language: str, raw_json: dict):
    db_text = await db.get(TextItem, text_id)
    if db_text is None:
        db.add(TextItem(id=text_id, text=text, language=language, raw_json=raw_json))
    else:
        db_text.text = text
        db_text.language = language
        db_text.raw_json = raw_json


async def list_texts(db: AsyncSession, page: int = 0, q: str = '', page_size: int = 50, task_id: str | None = None) -> dict:
    ann_q = (
        select(Annotation.text_id, func.count().label('ann_count'))
        .where(Annotation.annotation_type == AnnotationType.user)
    )
    if task_id:
        ann_q = ann_q.where(Annotation.task_id == task_id)
    ann_subq = ann_q.group_by(Annotation.text_id).subquery()

    query = (
        select(TextItem, func.coalesce(ann_subq.c.ann_count, 0).label('annotation_count'))
        .outerjoin(ann_subq, TextItem.id == ann_subq.c.text_id)
        .order_by(TextItem.id)
    )
    if q:
        query = query.where(TextItem.text.ilike(f'%{q}%'))
    total_q = select(func.count()).select_from(
        select(TextItem).where(TextItem.text.ilike(f'%{q}%')).subquery() if q
        else TextItem
    )
    total = (await db.execute(total_q)).scalar_one()
    rows = (await db.execute(query.offset(page * page_size).limit(page_size))).all()
    return {
        "total": total,
        "items": [
            {"id": t.id, "text_preview": t.text[:120], "language": t.language, "suspended": t.suspended, "annotation_count": ann_count}
            for t, ann_count in rows
        ],
    }


async def set_text_suspended(db: AsyncSession, text_id: str, suspended: bool) -> bool:
    item = await db.get(TextItem, text_id)
    if item is None:
        return False
    item.suspended = suspended
    return True


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

async def _user_annotation_count(db: AsyncSession, user_id, task_id: str) -> int:
    return (await db.execute(
        select(func.count()).select_from(Annotation)
        .where(Annotation.user_id == user_id, Annotation.task_id == task_id)
    )).scalar_one()


async def _pick_calibration_text(
    db: AsyncSession, user_id, calib_task_ids: list[str]
) -> tuple[TextItem | None, list[str]]:
    gt_texts_q = (
        select(Annotation.text_id, func.count(Annotation.task_id).label("gt_count"))
        .where(
            Annotation.annotation_type == AnnotationType.ground_truth,
            Annotation.task_id.in_(calib_task_ids),
        )
        .group_by(Annotation.text_id)
        .subquery()
    )
    user_seen = select(Annotation.text_id).where(
        Annotation.user_id == user_id,
        Annotation.task_id.in_(calib_task_ids),
    ).subquery()
    q = (
        select(TextItem, gt_texts_q.c.gt_count)
        .join(gt_texts_q, TextItem.id == gt_texts_q.c.text_id)
        .where(TextItem.id.not_in(select(user_seen.c.text_id)))
        .where(TextItem.suspended.is_(False))
        .order_by(gt_texts_q.c.gt_count.desc(), TextItem.id.asc())
        .limit(1)
    )
    row = (await db.execute(q)).first()
    if row is None:
        return None, []
    text_item = row[0]
    covered = (await db.execute(
        select(Annotation.task_id)
        .where(
            Annotation.text_id == text_item.id,
            Annotation.annotation_type == AnnotationType.ground_truth,
            Annotation.task_id.in_(calib_task_ids),
        )
    )).scalars().all()
    return text_item, list(covered)


async def _annotators_per_text_task(
    db: AsyncSession, task_ids,
) -> dict[tuple[str, str], set]:
    """Return {(text_id, task_id): {user_id, ...}} of distinct users with `user` annotations."""
    rows = (await db.execute(
        select(Annotation.text_id, Annotation.task_id, Annotation.user_id)
        .where(Annotation.task_id.in_(list(task_ids)),
               Annotation.annotation_type == AnnotationType.user)
        .distinct()
    )).all()
    result: dict[tuple[str, str], set] = defaultdict(set)
    for text_id, task_id, user_id in rows:
        result[(text_id, task_id)].add(user_id)
    return result


def _score_text(
    text_id: str, user_id, targets: dict[str, int], annotators: dict[tuple[str, str], set],
) -> int:
    """Usefulness of `user_id` annotating `text_id` for the tasks in `targets`.

    For every task still below its target of unique annotators (and not yet
    annotated by this user) the text gets 1 + current count, so texts closer to
    completion are preferred and texts useful for more of the user's tasks win.
    """
    score = 0
    for task_id, target in targets.items():
        users = annotators.get((text_id, task_id), ())
        if user_id in users:
            continue
        n = len(users)
        if n < target:
            score += 1 + n
    return score


async def _pick_fill_text(
    db: AsyncSession, user_id, task_ids: list[str], targets: dict[str, int], store: ReservationStore,
) -> TextItem | None:
    active_ids = (await db.execute(
        select(TextItem.id).where(TextItem.suspended.is_(False))
    )).scalars().all()
    if not active_ids:
        return None

    annotators = await _annotators_per_text_task(db, targets.keys())
    for key, users in store.pending(exclude_user=user_id).items():
        if key[1] in targets:
            annotators[key] = annotators[key] | users

    best_score, best = 0, []
    for text_id in active_ids:
        s = _score_text(text_id, user_id, targets, annotators)
        if s > best_score:
            best_score, best = s, [text_id]
        elif s == best_score and s > 0:
            best.append(text_id)

    if not best:
        # Everything the user can contribute to is saturated: fall back to a
        # random text, preferring ones the user has not annotated yet.
        seen = {
            text_id for (text_id, task_id), users in annotators.items()
            if task_id in task_ids and user_id in users
        }
        unseen = [t for t in active_ids if t not in seen]
        best = unseen or list(active_ids)
        logging.info(f"All texts saturated for user {user_id} and tasks {task_ids}; random fallback")

    return await db.get(TextItem, random.choice(best))


async def get_next_text(
    db: AsyncSession, user_id, task_ids: list[str], store: ReservationStore | None = None,
) -> tuple[TextItem | None, list[str]]:
    """ For a user and a set of task_ids, pick the next text to annotate.

    Rule ("fill up to target"): every task has `target_coverage` = desired number
    of unique annotators per text. Texts are scored by how much this user's
    annotation helps reach the targets of the user's selected tasks (see
    `_score_text`); the best-scoring text is chosen (random tie-break).
    Annotations from other users that are currently being made (soft
    reservations) count as if they were already done. If all texts are
    saturated, a random text is served.

    The picked text is soft-reserved for the user.

    Returns (text_item, calibration_task_ids).
    """
    store = store if store is not None else reservations

    tasks: Sequence[Task] = (await db.execute(
        select(Task).where(Task.id.in_(task_ids))
    )).scalars().all()
    targets = {t.id: t.target_coverage for t in tasks}

    """ Calibration is currently disabled.
    calib_task_ids: list[str] = []
    for tid in task_ids:
        task = task_map.get(tid)
        if task is None:
            continue
        user_count = await _user_annotation_count(db, user_id, tid)
        ratio = (
            task.calib_ratio_initial
            if user_count < task.calib_initial_count
            else task.calib_ratio_ongoing
        )
        if random.random() < ratio:
            calib_task_ids.append(tid)

    if calib_task_ids:
        text, covered = await _pick_calibration_text(db, user_id, calib_task_ids)
        if text is not None:
            return text, covered

    """
    text = await _pick_fill_text(db, user_id, task_ids, targets, store)
    if text is not None:
        store.reserve(user_id, text.id, targets.keys())
    logging.info(f"Picked text {text.id if text else None} for user {user_id} and tasks {task_ids}")
    return text, []


async def coverage_stats(db: AsyncSession) -> list[dict]:
    """Per enabled task: how many active texts reached the target of unique annotators."""
    tasks = await list_tasks(db, enabled_only=True)
    active_ids = (await db.execute(
        select(TextItem.id).where(TextItem.suspended.is_(False))
    )).scalars().all()
    annotators = await _annotators_per_text_task(db, [t.id for t in tasks])
    pending = reservations.pending()
    result = []
    for t in tasks:
        complete = partial = 0
        missing = 0
        for text_id in active_ids:
            n = len(annotators.get((text_id, t.id), ()))
            if n >= t.target_coverage:
                complete += 1
            else:
                missing += t.target_coverage - n
                if n > 0:
                    partial += 1
        result.append({
            'task_id': t.id,
            'task_name': t.name,
            'target': t.target_coverage,
            'active_texts': len(active_ids),
            'complete_texts': complete,
            'partial_texts': partial,
            'untouched_texts': len(active_ids) - complete - partial,
            'missing_annotations': missing,
            'pending_reservations': sum(
                len(u) for (txt, tid), u in pending.items() if tid == t.id
            ),
        })
    return result


# ---------------------------------------------------------------------------
# Points calculation
# ---------------------------------------------------------------------------

async def _compute_points(
    db: AsyncSession, user_id, text_id: str, task: Task, selected_classes: list[str]
) -> float:
    total_texts = (await db.execute(
        select(func.count()).select_from(TextItem).where(TextItem.suspended.is_(False))
    )).scalar_one()
    total_ann = (await db.execute(
        select(func.count()).select_from(Annotation)
        .where(Annotation.task_id == task.id, Annotation.annotation_type == AnnotationType.user)
    )).scalar_one()
    avg_coverage = total_ann / max(total_texts, 1)
    mult = _scarcity_multiplier(avg_coverage, task.target_coverage)
    K = 30.0 * mult

    rel_row = (await db.execute(
        select(UserReliability)
        .where(UserReliability.user_id == user_id, UserReliability.task_id == task.id)
    )).scalar_one_or_none()
    E = rel_row.pairwise_agreement if (rel_row and rel_row.pairwise_agreement is not None) else 0.5

    gt = (await db.execute(
        select(Annotation.selected_classes)
        .where(
            Annotation.text_id == text_id,
            Annotation.task_id == task.id,
            Annotation.annotation_type == AnnotationType.ground_truth,
        )
    )).scalar_one_or_none()

    if gt is not None:
        A = 1.0 if set(selected_classes) == set(gt) else 0.0
    else:
        existing = (await db.execute(
            select(Annotation.selected_classes, Annotation.weight)
            .where(
                Annotation.text_id == text_id,
                Annotation.task_id == task.id,
                Annotation.user_id != user_id,
                Annotation.annotation_type == AnnotationType.user,
            )
        )).all()
        if existing:
            class_weights: dict[str, float] = {}
            total_weight = sum(w for _, w in existing)
            for sc, w in existing:
                for cls in sc:
                    class_weights[cls] = class_weights.get(cls, 0.0) + w
            if total_weight > 0:
                best = max(class_weights, key=class_weights.__getitem__)
                A = (class_weights.get(best, 0.0) / total_weight) if best in selected_classes else 0.0
            else:
                A = 0.0
        else:
            A = 0.0

    base = 1.0
    delta = K * (A - E)
    return base + max(0.0, delta)


# ---------------------------------------------------------------------------
# Annotation CRUD
# ---------------------------------------------------------------------------

async def save_annotations(
    db: AsyncSession,
    user_id,
    payload: base_objects.AnnotationSubmit,
    tasks_map: dict[str, Task],
    annotation_type: AnnotationType = AnnotationType.user,
) -> dict[str, float]:
    points: dict[str, float] = {}
    annotation_ids: list[str] = []
    for ann in payload.annotations:
        task = tasks_map[ann.task_id]
        selected = ann.selected_classes
        allowed_classes = {item['id'] for item in task.classes}
        unknown_classes = sorted(set(selected) - allowed_classes)
        if unknown_classes:
            raise ValueError(f"Task {task.id} has unknown classes: {', '.join(unknown_classes)}")
        if task.multi_choice:
            if not selected:
                raise ValueError(f"Task {task.id} requires at least one choice")
            if len(selected) > task.max_choices:
                raise ValueError(f"Task {task.id} allows max {task.max_choices} choices")
        elif len(selected) != 1:
            raise ValueError(f"Task {task.id} requires exactly one choice")

        pts = None
        if annotation_type == AnnotationType.user:
            pts = await _compute_points(db, user_id, payload.text_id, task, selected)
            points[ann.task_id] = pts

        row = Annotation(
            id=uuid.uuid4(),
            user_id=user_id,
            text_id=payload.text_id,
            task_id=ann.task_id,
            selected_classes=selected,
            start_time=ann.start_time,
            end_time=ann.end_time,
            annotation_type=annotation_type,
            points_earned=pts,
        )
        db.add(row)
        annotation_ids.append(str(row.id))

    if payload.session is not None:
        await _save_annotation_session(db, user_id, payload, annotation_ids)
    return points


async def _save_annotation_session(
    db: AsyncSession, user_id, payload: base_objects.AnnotationSubmit, annotation_ids: list[str],
) -> None:
    session = payload.session
    if await db.get(AnnotationSession, session.id) is not None:
        raise ValueError(f"Annotation session {session.id} was already submitted")
    db.add(AnnotationSession(
        id=session.id,
        user_id=user_id,
        text_id=payload.text_id,
        task_ids=[a.task_id for a in payload.annotations],
        annotation_ids=annotation_ids,
        client_started_at=_naive_utc(session.client_started_at),
        events=[e.model_dump(exclude_none=True) for e in session.events],
    ))


def _naive_utc(dt: datetime) -> datetime:
    """Store datetimes as naive UTC, like the rest of the DB."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def bulk_upsert_annotations(
    db: AsyncSession,
    items: list[base_objects.BulkAnnotationItem],
    annotation_type: AnnotationType,
    submitter_user_id: uuid.UUID,
) -> int:
    count = 0
    now = datetime.utcnow()
    for item in items:
        existing = (await db.execute(
            select(Annotation).where(
                Annotation.user_id == submitter_user_id,
                Annotation.text_id == item.text_id,
                Annotation.task_id == item.task_id,
                Annotation.annotation_type == annotation_type,
            )
        )).scalar_one_or_none()
        if existing:
            existing.selected_classes = item.selected_classes
        else:
            db.add(Annotation(
                user_id=submitter_user_id,
                text_id=item.text_id,
                task_id=item.task_id,
                selected_classes=item.selected_classes,
                start_time=now,
                end_time=now,
                annotation_type=annotation_type,
            ))
        count += 1
    return count


async def set_annotation_type(
    db: AsyncSession, annotation_id: uuid.UUID, annotation_type: AnnotationType
) -> bool:
    ann = await db.get(Annotation, annotation_id)
    if ann is None:
        return False
    ann.annotation_type = annotation_type
    return True


async def get_gt_for_text_tasks(
    db: AsyncSession, text_id: str, task_ids: list[str]
) -> dict[str, list[str]]:
    rows = (await db.execute(
        select(Annotation.task_id, Annotation.selected_classes)
        .where(
            Annotation.text_id == text_id,
            Annotation.task_id.in_(task_ids),
            Annotation.annotation_type == AnnotationType.ground_truth,
        )
    )).all()
    return {tid: sc for tid, sc in rows}


# ---------------------------------------------------------------------------
# Stats & leaderboard
# ---------------------------------------------------------------------------

async def my_stats(db: AsyncSession, user_id) -> dict:
    per_task_q = await db.execute(
        select(
            Annotation.task_id,
            func.count(),
            func.coalesce(func.sum(Annotation.points_earned), 0),
        )
        .where(Annotation.user_id == user_id, Annotation.annotation_type == AnnotationType.user)
        .group_by(Annotation.task_id)
    )
    rows = per_task_q.all()
    totals = {task_id: count for task_id, count, _ in rows}
    scores = {task_id: float(score) for task_id, _, score in rows}
    return {
        "total": sum(totals.values()),
        "per_task": totals,
        "score": sum(scores.values()),
        "per_task_score": scores,
    }


async def leaderboard(db: AsyncSession, task_id: str, since: datetime | None = None) -> list[dict]:
    rel_subq = (
        select(UserReliability.user_id, UserReliability.pairwise_agreement)
        .where(UserReliability.task_id == task_id)
        .subquery()
    )
    q = (
        select(
            Annotation.user_id,
            func.count().label("count"),
            func.coalesce(func.sum(Annotation.points_earned), 0).label("score"),
            User.display_name,
            rel_subq.c.pairwise_agreement,
        )
        .outerjoin(User, User.id == Annotation.user_id)
        .outerjoin(rel_subq, rel_subq.c.user_id == Annotation.user_id)
        .where(Annotation.task_id == task_id, Annotation.annotation_type == AnnotationType.user)
    )
    if since:
        q = q.where(Annotation.created_at >= since)
    q = (q.group_by(Annotation.user_id, User.display_name, rel_subq.c.pairwise_agreement)
         .order_by(func.sum(Annotation.points_earned).desc().nulls_last(), func.count().desc())
         .limit(20))
    rows = await db.execute(q)
    return [
        {"user_id": str(u), "display_name": _display_name(dn, u), "count": c, "score": float(s),
         "reliability": float(pa) if pa is not None else None}
        for u, c, s, dn, pa in rows.all()
    ]


async def leaderboard_overall(db: AsyncSession, since: datetime | None = None) -> list[dict]:
    avg_rel_subq = (
        select(UserReliability.user_id, func.avg(UserReliability.pairwise_agreement).label("avg_reliability"))
        .group_by(UserReliability.user_id)
        .subquery()
    )
    q = (
        select(
            Annotation.user_id,
            func.count().label("count"),
            func.coalesce(func.sum(Annotation.points_earned), 0).label("score"),
            User.display_name,
            avg_rel_subq.c.avg_reliability,
        )
        .outerjoin(User, User.id == Annotation.user_id)
        .outerjoin(avg_rel_subq, avg_rel_subq.c.user_id == Annotation.user_id)
        .where(Annotation.annotation_type == AnnotationType.user)
    )
    if since:
        q = q.where(Annotation.created_at >= since)
    q = (q.group_by(Annotation.user_id, User.display_name, avg_rel_subq.c.avg_reliability)
         .order_by(func.sum(Annotation.points_earned).desc().nulls_last(), func.count().desc())
         .limit(20))
    rows = await db.execute(q)
    return [
        {"user_id": str(u), "display_name": _display_name(dn, u), "count": c, "score": float(s),
         "reliability": float(ar) if ar is not None else None}
        for u, c, s, dn, ar in rows.all()
    ]


async def global_stats(db: AsyncSession) -> dict:
    task_rows = await db.execute(
        select(Annotation.task_id, Task.name, func.count(Annotation.id).label("count"))
        .join(Task, Task.id == Annotation.task_id)
        .where(Annotation.annotation_type == AnnotationType.user)
        .group_by(Annotation.task_id, Task.name)
        .order_by(func.count(Annotation.id).desc())
    )
    total_row = await db.execute(
        select(func.count()).select_from(Annotation)
        .where(Annotation.annotation_type == AnnotationType.user)
    )
    return {
        "total_annotations": total_row.scalar_one(),
        "per_task": [{"task_id": tid, "task_name": name, "count": c} for tid, name, c in task_rows.all()],
    }


async def get_text_annotations(
    db: AsyncSession, text_id: str, task_id: str | None = None
) -> list[dict]:
    q = (
        select(Annotation, User.display_name)
        .outerjoin(User, User.id == Annotation.user_id)
        .where(Annotation.text_id == text_id)
    )
    if task_id:
        q = q.where(Annotation.task_id == task_id)
    q = q.order_by(Annotation.task_id, Annotation.annotation_type, Annotation.created_at)
    rows = (await db.execute(q)).all()
    return [
        {
            "annotation_id": str(ann.id),
            "user_id": str(ann.user_id),
            "display_name": _display_name(dn, ann.user_id),
            "task_id": ann.task_id,
            "selected_classes": ann.selected_classes,
            "annotation_type": ann.annotation_type.value,
            "created_at": ann.created_at.isoformat() if ann.created_at else None,
            "points_earned": float(ann.points_earned) if ann.points_earned is not None else None,
        }
        for ann, dn in rows
    ]


async def get_text_sessions(db: AsyncSession, text_id: str) -> list[dict]:
    """Annotation sessions of a text with their annotations and voice comment (admin view)."""
    rows = (await db.execute(
        select(AnnotationSession, User.display_name, VoiceComment)
        .outerjoin(User, User.id == AnnotationSession.user_id)
        .outerjoin(VoiceComment, VoiceComment.session_id == AnnotationSession.id)
        .where(AnnotationSession.text_id == text_id)
        .order_by(AnnotationSession.submitted_at)
    )).all()
    ann_ids = [uuid.UUID(a) for s, _, _ in rows for a in s.annotation_ids]
    anns: dict[str, Annotation] = {}
    if ann_ids:
        anns = {str(a.id): a for a in (await db.execute(select(Annotation).where(Annotation.id.in_(ann_ids)))).scalars()}
    result = []
    for s, dn, vc in rows:
        name = _display_name(dn, s.user_id)
        result.append({
            "session_id": str(s.id),
            "user_id": str(s.user_id),
            "display_name": name,
            "text_id": s.text_id,
            "task_ids": s.task_ids,
            "client_started_at": s.client_started_at,
            "submitted_at": s.submitted_at,
            "events": s.events,
            "annotations": [
                {
                    "annotation_id": str(a.id),
                    "user_id": str(a.user_id),
                    "display_name": name,
                    "task_id": a.task_id,
                    "selected_classes": a.selected_classes,
                    "annotation_type": a.annotation_type.value,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "points_earned": float(a.points_earned) if a.points_earned is not None else None,
                }
                for a in (anns.get(i) for i in s.annotation_ids) if a is not None
            ],
            "voice_comment": voice_comment_entry(vc) if vc is not None else None,
        })
    return result


def voice_comment_entry(vc: VoiceComment) -> dict:
    return {
        "id": str(vc.id),
        "language": vc.language,
        "mime_type": vc.mime_type,
        "size_bytes": vc.size_bytes,
        "start_ms": vc.start_ms,
        "end_ms": vc.end_ms,
        "created_at": vc.created_at,
        "transcription_status": vc.transcription_status.value,
        "transcription_attempts": vc.transcription_attempts,
        "transcription_error": vc.transcription_error,
        "transcription_model": vc.transcription_model,
        "transcript": vc.transcript,
        "transcript_segments": vc.transcript_segments,
        "transcribed_at": vc.transcribed_at,
    }


# ---------------------------------------------------------------------------
# User reliability queries
# ---------------------------------------------------------------------------

async def get_reliability(
    db: AsyncSession, user_id=None, task_id: str | None = None
) -> list[dict]:
    q = select(UserReliability, User.display_name).outerjoin(User, User.id == UserReliability.user_id)
    if user_id is not None:
        q = q.where(UserReliability.user_id == user_id)
    if task_id is not None:
        q = q.where(UserReliability.task_id == task_id)
    rows = (await db.execute(q)).all()
    return [
        {
            "user_id": str(r.user_id),
            "display_name": _display_name(dn, r.user_id),
            "task_id": r.task_id,
            "annotation_count": r.annotation_count,
            "pairwise_agreement": r.pairwise_agreement,
            "cohens_kappa": r.cohens_kappa,
            "krippendorffs_alpha": r.krippendorffs_alpha,
            "ds_sensitivity": r.ds_sensitivity,
            "computed_at": r.computed_at,
        }
        for r, dn in rows
    ]




