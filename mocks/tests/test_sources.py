"""Ответы источников на синтетических данных."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import KEY


def credit_report_request(inn: str, given_at: datetime | None = None, given: bool = True) -> dict:
    return {
        "inn": inn,
        "subject_type": "legal_entity" if len(inn) == 10 else "individual_entrepreneur",
        "consent": {
            "given": given,
            "given_at": (given_at or datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "purpose": "loan_application",
        },
    }


def test_health_needs_no_key(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["records"] == {"egr": 5, "nbki": 5, "pb": 5}


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/egr/v1/extracts/1655482318", None),
        ("POST", "/nbki/v1/credit-reports", credit_report_request("1655482318")),
        ("GET", "/pb/v1/companies/1655482318", None),
        ("GET", "/admin/sources", None),
    ],
)
def test_api_key_is_required(client: TestClient, method: str, path: str, payload: dict | None) -> None:
    for headers in ({}, {"X-Api-Key": "wrong"}):
        response = client.request(method, path, json=payload, headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_egrul_extract(client: TestClient) -> None:
    body = client.get("/egr/v1/extracts/1655482318", headers=KEY).json()
    assert body["registry"] == "EGRUL"
    assert body["status"]["code"] == "active"
    assert body["head"]["position"] == "Генеральный директор"
    assert body["request_id"]


def test_egrip_extract_for_entrepreneur(client: TestClient) -> None:
    body = client.get("/egr/v1/extracts/504718329642", headers=KEY).json()
    assert body["registry"] == "EGRIP"
    assert body["head"] is None
    assert body["kpp"] is None


def test_liquidated_company(client: TestClient) -> None:
    status = client.get("/egr/v1/extracts/6671034827", headers=KEY).json()["status"]
    assert status["code"] == "liquidated"
    assert status["changed_at"] == "2026-08-14"


def test_unknown_and_malformed_inn(client: TestClient) -> None:
    unknown = client.get("/egr/v1/extracts/7700000001", headers=KEY)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"
    assert client.get("/egr/v1/extracts/123", headers=KEY).status_code == 400


def test_credit_report(client: TestClient) -> None:
    body = client.post("/nbki/v1/credit-reports", json=credit_report_request("1655482318"), headers=KEY).json()
    assert body["history_found"] is True
    assert body["report_id"].startswith("NBKI-")
    active_payments = sum(loan["monthly_payment"] for loan in body["loans"] if loan["status"] == "active")
    assert active_payments == 720_000  # совпадает с демо-заявкой A-1024


def test_no_credit_history_is_a_result_not_an_error(client: TestClient) -> None:
    response = client.post("/nbki/v1/credit-reports", json=credit_report_request("7700000001"), headers=KEY)
    assert response.status_code == 200
    assert response.json()["history_found"] is False
    assert response.json()["loans"] == []


def test_credit_report_requires_valid_consent(client: TestClient) -> None:
    no_consent = client.post("/nbki/v1/credit-reports", json=credit_report_request("1655482318", given=False), headers=KEY)
    assert no_consent.status_code == 403
    assert no_consent.json()["error"]["code"] == "consent_required"

    old = credit_report_request("1655482318", given_at=datetime.now(UTC) - timedelta(days=200))
    expired = client.post("/nbki/v1/credit-reports", json=old, headers=KEY)
    assert expired.status_code == 403
    assert expired.json()["error"]["code"] == "consent_expired"


def test_credit_report_checks_subject_type(client: TestClient) -> None:
    payload = credit_report_request("1655482318") | {"subject_type": "individual_entrepreneur"}
    response = client.post("/nbki/v1/credit-reports", json=payload, headers=KEY)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "subject_type_mismatch"


def test_transparent_business_risk_markers(client: TestClient) -> None:
    body = client.get("/pb/v1/companies/5406247181", headers=KEY).json()
    assert body["mass_address"] == {"flag": True, "companies_count": 54}
    clean = client.get("/pb/v1/companies/7810624578", headers=KEY).json()
    assert clean["mass_address"]["flag"] is False
    assert clean["tax_arrears"]["has_arrears"] is False
