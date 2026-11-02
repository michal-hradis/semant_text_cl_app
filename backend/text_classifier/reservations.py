"""In-memory soft reservations of texts served for annotation.

When a text is served to a user for a set of tasks, it is reserved for a
limited time so that concurrent users see it as "pending" when the sampler
counts annotators per (text, task). This reduces overshooting the target
number of annotations when several users request texts at the same time.

Each user holds at most one reservation (requesting a new text replaces the
old one; submitting annotations releases it).

Limitation: state lives in the process memory, so it is only correct with a
single worker process and is lost on restart (which is harmless — reservations
are only a hint).
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable


@dataclass(frozen=True)
class Reservation:
    text_id: str
    task_ids: frozenset[str]
    expires_at: float


class ReservationStore:
    def __init__(self, ttl_seconds: float, clock=time.monotonic):
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._by_user: dict[Hashable, Reservation] = {}

    def _purge(self) -> None:
        now = self._clock()
        expired = [u for u, r in self._by_user.items() if r.expires_at <= now]
        for u in expired:
            del self._by_user[u]

    def reserve(self, user_id: Hashable, text_id: str, task_ids) -> None:
        self._by_user[user_id] = Reservation(
            text_id=text_id,
            task_ids=frozenset(task_ids),
            expires_at=self._clock() + self.ttl_seconds,
        )

    def release(self, user_id: Hashable) -> None:
        self._by_user.pop(user_id, None)

    def pending(self, exclude_user: Hashable | None = None) -> dict[tuple[str, str], set]:
        """Return {(text_id, task_id): {user_id, ...}} of active reservations."""
        self._purge()
        result: dict[tuple[str, str], set] = defaultdict(set)
        for user_id, r in self._by_user.items():
            if user_id == exclude_user:
                continue
            for task_id in r.task_ids:
                result[(r.text_id, task_id)].add(user_id)
        return result

    def clear(self) -> None:
        self._by_user.clear()


def _default_ttl() -> float:
    from text_classifier.config import config
    return float(config.RESERVATION_TTL_SECONDS)


reservations = ReservationStore(ttl_seconds=_default_ttl())
