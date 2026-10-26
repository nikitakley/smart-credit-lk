"""Адаптеры внешних источников: повторы и таймауты, разбор ответов, совместимость с симулятором."""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.integrations.egr import fetch_registry_info
from app.integrations.http import SourceUnavailable, request_json
from app.integrations.nbki import fetch_credit_history
from app.integrations.pb import fetch_risk_profile
from app.schemas.enums import CompanyType

URL = "http://source.test/v1/item"


def fake_source(*responses: Callable[[httpx.Request], httpx.Response]) -> tuple[httpx.Client, list[httpx.Request]]:
    """Клиент, который вместо сети по очереди отдаёт заданные ответы и запоминает запросы."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[min(len(calls), len(responses)) - 1](request)

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def status(code: int, body: dict | None = None) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(code, json=body or {})


def timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("no answer", request=request)


# --- [Повторы и обработка ошибок]


def test_retry_after_temporary_failure() -> None:
    client, calls = fake_source(status(503), status(200, {"ok": True}))
    assert request_json(client, "test", "GET", URL) == {"ok": True}
    assert len(calls) == 2


def test_gives_up_after_all_attempts() -> None:
    client, calls = fake_source(status(503))
    with pytest.raises(SourceUnavailable) as error:
        request_json(client, "test", "GET", URL)
    assert error.value.reason == "http_503"
    assert len(calls) == get_settings().integration_retries + 1
    # Все попытки — с одним идентификатором: в журналах это один логический запрос
    assert len({request.headers["X-Request-Id"] for request in calls}) == 1


def test_timeout_is_retried() -> None:
    client, calls = fake_source(timeout, timeout, status(200, {"ok": True}))
    assert request_json(client, "test", "GET", URL) == {"ok": True}
    assert len(calls) == 3


def test_client_errors_are_not_retried() -> None:
    client, calls = fake_source(status(401))
    with pytest.raises(SourceUnavailable) as error:
        request_json(client, "test", "GET", URL)
    assert error.value.reason == "http_401"
    assert len(calls) == 1  # неверный ключ со второй попытки верным не станет


def test_not_found_is_an_answer() -> None:
    client, calls = fake_source(status(404))
    assert request_json(client, "test", "GET", URL) is None
    assert len(calls) == 1


def test_unexpected_response_format() -> None:
    client, _ = fake_source(status(200, {"something": "else"}))
    with pytest.raises(SourceUnavailable) as error:
        fetch_registry_info(client, "1655482318")
    assert error.value.reason == "invalid_response"


# --- [Совместимость с симулятором]


def test_registry_info(simulator: TestClient) -> None:
    info = fetch_registry_info(simulator, "6671034827")
    assert info.found and info.registry == "egrul"
    assert info.status == "liquidated"
    assert info.age_months is not None and info.age_months > 100

    entrepreneur = fetch_registry_info(simulator, "504718329642")
    assert entrepreneur.registry == "egrip"
    assert entrepreneur.head is None

    assert fetch_registry_info(simulator, "7700000001").found is False


def test_credit_history(simulator: TestClient) -> None:
    history = fetch_credit_history(simulator, "1655482318", CompanyType.legal, datetime.now(UTC))
    assert history.history_found
    assert history.monthly_payments == 720_000  # как в демо-заявке A-1024
    assert history.active_loans == 2
    assert history.overdues_24m == 0

    entrepreneur = fetch_credit_history(simulator, "504718329642", CompanyType.ip, datetime.now(UTC))
    assert entrepreneur.history_months == 11

    unknown = fetch_credit_history(simulator, "7700000001", CompanyType.legal, datetime.now(UTC))
    assert unknown.history_found is False


def test_risk_profile(simulator: TestClient) -> None:
    profile = fetch_risk_profile(simulator, "5406247181")
    assert profile.mass_address_companies == 54
    assert profile.report_year == 2025

    liquidated = fetch_risk_profile(simulator, "6671034827")
    assert liquidated.unreliable_info == ["адрес"]
    assert liquidated.tax_arrears == 412_300


def test_source_outage_is_reported(simulator: TestClient) -> None:
    simulator.put("/admin/sources/pb", json={"mode": "error"})
    with pytest.raises(SourceUnavailable) as error:
        fetch_risk_profile(simulator, "5406247181")
    assert error.value.reason == "http_503"


def test_wrong_api_key_is_not_retried(simulator: TestClient) -> None:
    simulator.headers["X-Api-Key"] = "wrong"
    with pytest.raises(SourceUnavailable) as error:
        fetch_registry_info(simulator, "1655482318")
    assert error.value.reason == "http_401"
