"""Управление симулятором: поведение источников и журнал запросов. Только для разработки и демо."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from simulator.faults import Source, SourceBehavior, SourceBehaviorUpdate, get_faults
from simulator.journal import JournalEntry, get_journal
from simulator.security import require_api_key

router = APIRouter(prefix="/admin", tags=["Управление симулятором"], dependencies=[Depends(require_api_key)])


@router.get("/sources", response_model=dict[Source, SourceBehavior], summary="Текущее поведение источников")
def sources() -> dict[Source, SourceBehavior]:
    return get_faults().behaviors


@router.put(
    "/sources/{source}",
    response_model=SourceBehavior,
    summary="Изменить поведение источника",
    description="Например, `{\"mode\": \"error\"}` — источник недоступен; `{\"mode\": \"normal\"}` — вернуть как было.",
)
def update_source(source: Source, change: SourceBehaviorUpdate) -> SourceBehavior:
    return get_faults().update(source, change)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT, summary="Сбросить поведение и журнал")
def reset() -> None:
    get_faults().reset()
    get_journal().clear()


@router.get("/requests", response_model=list[JournalEntry], summary="Последние запросы к источникам")
def requests(limit: Annotated[int, Query(ge=1, le=200)] = 50) -> list[JournalEntry]:
    return get_journal().latest(limit)
