"""ЕГРЮЛ / ЕГРИП: существование, статус и регистрационные данные бизнеса."""

from datetime import date
from typing import Literal

import httpx2 as httpx
from pydantic import BaseModel

from app.config import get_settings
from app.integrations.http import parse_response, request_json
from app.schemas.checks import RegistryDetails

SOURCE = "egr"

RegistryStatus = Literal["active", "liquidating", "liquidated", "reorganizing", "bankrupt"]


# --- [Формат источника: только нужные поля, остальные игнорируются]


class _Status(BaseModel):
    code: RegistryStatus
    name: str
    changed_at: date | None = None


class _Head(BaseModel):
    full_name: str
    position: str


class _Okved(BaseModel):
    code: str
    title: str


class _Address(BaseModel):
    text: str


class _Extract(BaseModel):
    registry: Literal["EGRUL", "EGRIP"]
    inn: str
    ogrn: str
    registration_date: date
    status: _Status
    head: _Head | None
    okved_main: _Okved
    address: _Address
    extract_date: date


# --- [Перевод во внутренний формат банка (app/schemas/checks.py)]


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def fetch_registry_info(client: httpx.Client, inn: str) -> RegistryDetails:
    url = f"{get_settings().egr_base_url}/v1/extracts/{inn}"
    data = request_json(client, SOURCE, "GET", url)
    if data is None:
        return RegistryDetails(found=False)
    extract = parse_response(SOURCE, _Extract, data)
    return RegistryDetails(
        found=True,
        registry="egrul" if extract.registry == "EGRUL" else "egrip",
        ogrn=extract.ogrn,
        status=extract.status.code,
        status_name=extract.status.name,
        status_changed_at=extract.status.changed_at,
        registered_at=extract.registration_date,
        age_months=_months_between(extract.registration_date, extract.extract_date),
        head=extract.head.full_name if extract.head else None,
        head_position=extract.head.position if extract.head else None,
        okved=f"{extract.okved_main.code} {extract.okved_main.title}",
        address=extract.address.text,
    )
