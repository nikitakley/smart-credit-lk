"""ФНС «Прозрачный бизнес»: признаки риска, налоговый режим, отчётность."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Path

from simulator.errors import SourceError
from simulator.faults import Source
from simulator.models import INN_PATTERN, ErrorResponse, PbProfile
from simulator.security import source_guard
from simulator.store import get_store

router = APIRouter(prefix="/pb/v1", tags=["ФНС «Прозрачный бизнес»"], dependencies=[source_guard(Source.pb)])


@router.get(
    "/companies/{inn}",
    response_model=PbProfile,
    summary="Сведения о компании или ИП по ИНН",
    responses={404: {"model": ErrorResponse, "description": "Сведения не найдены"}},
)
async def company(inn: Annotated[str, Path(pattern=INN_PATTERN, examples=["5406247181"])]) -> PbProfile:
    record = get_store().pb.get(inn)
    if record is None:
        raise SourceError(404, "not_found", "Сведения по ИНН не найдены")
    return PbProfile(**record.model_dump(), request_id=str(uuid.uuid4()), checked_at=datetime.now(UTC))
