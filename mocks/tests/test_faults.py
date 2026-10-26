"""Имитация сбоев: недоступность, зависание, случайные ошибки, журнал запросов."""

from fastapi.testclient import TestClient

from simulator.config import get_settings
from tests.conftest import KEY

PB_URL = "/pb/v1/companies/7810624578"


def test_error_mode_makes_only_this_source_unavailable(client: TestClient) -> None:
    assert client.put("/admin/sources/pb", json={"mode": "error"}, headers=KEY).status_code == 200

    response = client.get(PB_URL, headers=KEY)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    # Остальные источники работают
    assert client.get("/egr/v1/extracts/7810624578", headers=KEY).status_code == 200

    client.put("/admin/sources/pb", json={"mode": "normal"}, headers=KEY)
    assert client.get(PB_URL, headers=KEY).status_code == 200


def test_timeout_mode(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "mock_timeout_seconds", 0.05)  # не ждать 30 секунд в тесте
    client.put("/admin/sources/pb", json={"mode": "timeout"}, headers=KEY)
    response = client.get(PB_URL, headers=KEY)
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "gateway_timeout"


def test_failure_rate(client: TestClient) -> None:
    client.put("/admin/sources/pb", json={"failure_rate": 1.0}, headers=KEY)
    assert client.get(PB_URL, headers=KEY).status_code == 503


def test_partial_update_keeps_other_settings(client: TestClient) -> None:
    client.put("/admin/sources/nbki", json={"latency_min_ms": 0, "latency_max_ms": 5}, headers=KEY)
    behavior = client.put("/admin/sources/nbki", json={"failure_rate": 0.2}, headers=KEY).json()
    assert behavior == {"mode": "normal", "latency_min_ms": 0, "latency_max_ms": 5, "failure_rate": 0.2}


def test_invalid_behavior_is_rejected(client: TestClient) -> None:
    response = client.put("/admin/sources/nbki", json={"latency_min_ms": 900, "latency_max_ms": 100}, headers=KEY)
    assert response.status_code == 400
    response = client.put("/admin/sources/nbki", json={"failure_rate": 2}, headers=KEY)
    assert response.status_code == 400


def test_reset_restores_defaults(client: TestClient) -> None:
    client.put("/admin/sources/egr", json={"mode": "error"}, headers=KEY)
    assert client.post("/admin/reset", headers=KEY).status_code == 204
    assert client.get("/admin/sources", headers=KEY).json()["egr"]["mode"] == "normal"


def test_journal_keeps_request_id(client: TestClient) -> None:
    response = client.get(PB_URL, headers=KEY | {"X-Request-Id": "trace-42"})
    assert response.headers["X-Request-Id"] == "trace-42"

    entry = client.get("/admin/requests?limit=1", headers=KEY).json()[0]
    assert entry["request_id"] == "trace-42"
    assert (entry["source"], entry["status"], entry["path"]) == ("pb", 200, PB_URL)
    # Служебные запросы в журнал не попадают
    assert all(e["source"] in {"egr", "nbki", "pb"} for e in client.get("/admin/requests", headers=KEY).json())
