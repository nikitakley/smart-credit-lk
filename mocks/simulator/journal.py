"""Журнал последних запросов к источникам — видно, что и когда запрашивал банк."""

from collections import deque
from datetime import datetime
from functools import lru_cache

from pydantic import BaseModel


class JournalEntry(BaseModel):
    at: datetime
    source: str
    method: str
    path: str
    status: int
    duration_ms: int
    request_id: str


class Journal:
    def __init__(self, size: int = 200) -> None:
        # deque с maxlen сам удаляет самые старые записи: память не растёт бесконечно
        self._entries: deque[JournalEntry] = deque(maxlen=size)

    def add(self, entry: JournalEntry) -> None:
        self._entries.append(entry)

    def latest(self, limit: int) -> list[JournalEntry]:
        return list(reversed(self._entries))[:limit]

    def clear(self) -> None:
        self._entries.clear()


@lru_cache
def get_journal() -> Journal:
    return Journal()
