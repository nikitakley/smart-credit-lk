"""ЕГРЮЛ / ЕГРИП: выписка из реестра по ИНН."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Path

from simulator.errors import SourceError
from simulator.faults import Source
from simulator.models import INN_PATTERN, EgrExtract, ErrorResponse
from simulator.security import source_guard
from simulator.store import get_store

router = APIRouter(prefix="/egr/v1", tags=["ЕГРЮЛ / ЕГРИП"], dependencies=[source_guard(Source.egr)])


@router.get(
    "/extracts/{inn}",
    response_model=EgrExtract,
    summary="Выписка из ЕГРЮЛ (10-значный ИНН) или ЕГРИП (12-значный ИНН)",
    responses={404: {"model": ErrorResponse, "description": "Сведения не найдены"}},
)
async def extract(inn: Annotated[str, Path(pattern=INN_PATTERN, examples=["1655482318"])]) -> EgrExtract:
    record = get_store().egr.get(inn)
    if record is None:
        raise SourceError(404, "not_found", "Сведения по ИНН в реестре не найдены")
    return EgrExtract(
        **record.model_dump(),
        request_id=str(uuid.uuid4()),
        extract_date=datetime.now(UTC).date(),
    )
