"""Small repository implementations used by the learning service tests.

These are lightweight and kept in a separate module so tests can import them directly
without pulling in the full learning service module.
"""
from __future__ import annotations

from typing import Dict, List

from app.services.learning_types import VerbbankData
from app.models import VerbbankEntry


class InMemoryVerbbankRepository:
    """A tiny in-memory VerbbankRepository used as a default when no repository is provided.

    It implements the minimal methods used by the service: upsert, search_for_user and delete_for_user.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, VerbbankEntry]] = {}

    def upsert(self, entry: VerbbankEntry) -> None:
        user = self._store.setdefault(entry.user_id, {})
        user[entry.verb] = entry

    def search_for_user(self, user_id: str, query: str = "", limit: int = 100) -> list[VerbbankEntry]:
        entries = list(self._store.get(user_id, {}).values())
        if query.strip():
            q = query.strip().casefold()
            entries = [
                e for e in entries
                if q in e.verb.casefold() or q in e.conjugations.casefold() or q in e.topic.casefold()
            ]
        entries.sort(key=lambda e: e.verb)
        return entries[:limit]

    def delete_for_user(self, user_id: str) -> None:
        self._store.pop(user_id, None)
