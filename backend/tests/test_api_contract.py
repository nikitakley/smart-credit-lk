"""Проверки контракта API: ответы, коды ошибок и сквозные сценарии на PostgreSQL."""

from fastapi.testclient import TestClient

from tests.conftest import login


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    response = client.get("/api/applications")
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthorized", "message": "Требуется вход в систему", "fields": []}}


def test_client_cannot_open_analyst_queue(client: TestClient, prodmarket: dict) -> None:
    assert client.get("/api/analyst/applications", headers=prodmarket).status_code == 403


def test_foreign_application_is_not_visible(client: TestClient, prodmarket: dict) -> None:
    response = client.get("/api/applications/A-1022", headers=prodmarket)  # заявка «Вектор Софт»
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "application_not_found"


def test_client_projection_hides_internal_fields(client: TestClient, prodmarket: dict) -> None:
    body = client.get("/api/applications/A-1024", headers=prodmarket).json()
    for field in ("score", "scoringInputs", "systemRecommendation", "rateBreakdown"):
        assert field not in body
    assert "points" not in body["factors"][0]
    assert "details" not in body["checks"][0]


def test_analyst_projection_is_full(client: TestClient, analyst: dict) -> None:
    body = client.get("/api/analyst/applications/A-1024", headers=analyst).json()
    assert body["score"]["value"] == 680
    assert body["systemRecommendation"]["outcome"] == "counter_offer"


def test_validation_error_format(client: TestClient) -> None:
    response = client.post("/api/assistant/recommend", json={"purpose": "unknown", "amount": -1, "termMonths": 12})
    assert response.status_code == 422
    fields = {f["field"] for f in response.json()["error"]["fields"]}
    assert {"purpose", "amount"} <= fields


def test_recommend(client: TestClient) -> None:
    body = client.post(
        "/api/assistant/recommend",
        json={"purpose": "cash_gap", "amount": 400000, "termMonths": 12, "collateral": "none"},
    ).json()
    assert body["items"][0]["product"]["id"] == "overdraft"
    assert body["items"][0]["best"] is True


def test_draft_to_submit_flow(client: TestClient, prodmarket: dict) -> None:
    draft = client.post("/api/applications", json={"productId": "working-capital"}, headers=prodmarket)
    assert draft.status_code == 201
    app_id = draft.json()["id"]
    assert draft.json()["status"] == "draft"

    # Отправка без обязательных полей и согласий
    early = client.post(f"/api/applications/{app_id}/submit",
                        json={"consents": {"bki": False, "personalData": True}}, headers=prodmarket)
    assert early.status_code == 422
    fields = {f["field"] for f in early.json()["error"]["fields"]}
    assert {"amount", "termMonths", "purpose", "contact", "consents.bki"} <= fields

    patched = client.patch(
        f"/api/applications/{app_id}",
        json={"amount": 1000000, "termMonths": 12, "purpose": "working_capital",
              "contact": {"name": "Иванов И. И.", "phone": "+7 900 000-00-01", "email": "a@b.ru"}},
        headers=prodmarket,
    )
    assert patched.status_code == 200

    headers = {**prodmarket, "Idempotency-Key": "test-key-1"}
    payload = {"consents": {"bki": True, "personalData": True}}
    first = client.post(f"/api/applications/{app_id}/submit", json=payload, headers=headers)
    second = client.post(f"/api/applications/{app_id}/submit", json=payload, headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json()["status"] == "submitted"
    assert second.json()["id"] == app_id

    # Отправленную заявку менять нельзя
    assert client.patch(f"/api/applications/{app_id}", json={"amount": 5}, headers=prodmarket).status_code == 409


def test_offer_sign_issue_flow(client: TestClient, prodmarket: dict) -> None:
    accepted = client.post("/api/applications/A-1024/offer/accept", headers=prodmarket)
    assert accepted.json()["status"] == "signing"

    wrong = client.post("/api/applications/A-1024/sign", json={"code": "000000"}, headers=prodmarket)
    assert wrong.status_code in (409, 422)  # 409, если код ещё не запрошен

    code = client.post("/api/applications/A-1024/sign/code", headers=prodmarket).json()["code"]
    bad = client.post("/api/applications/A-1024/sign",
                      json={"code": "999999" if code != "999999" else "000000"}, headers=prodmarket)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_code"

    signed = client.post("/api/applications/A-1024/sign", json={"code": code}, headers=prodmarket)
    assert signed.status_code == 200
    assert signed.json()["status"] == "issued"
    assert signed.json()["issuance"]["amount"] == 1_500_000


def test_info_request_flow(client: TestClient) -> None:
    sidorov = login(client, "sidorov")
    response = client.post(
        "/api/applications/A-1023/info",
        json={"answers": [{"code": "monthly_revenue_confirm", "value": "900000"},
                          {"code": "main_bank", "value": "Банк А"}]},
        headers=sidorov,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "validation"


def test_analyst_decision(client: TestClient, analyst: dict) -> None:
    no_comment = client.post("/api/analyst/applications/A-1025/decision",
                             json={"action": "counter_offer", "amount": 3000000}, headers=analyst)
    assert no_comment.status_code == 422

    decided = client.post(
        "/api/analyst/applications/A-1025/decision",
        json={"action": "counter_offer", "amount": 3000000, "commentForClient": "Снизили сумму из-за признаков риска"},
        headers=analyst,
    )
    assert decided.status_code == 200
    body = decided.json()
    assert body["status"] == "counter_offer"
    assert body["offer"]["amount"] == 3000000
    assert body["decision"]["decidedBy"] == "analyst"


def test_demo_reset(client: TestClient, prodmarket: dict) -> None:
    client.post("/api/applications/A-1024/offer/decline", headers=prodmarket)
    assert client.post("/api/demo/reset").status_code == 204
    assert client.get("/api/applications/A-1024", headers=prodmarket).json()["status"] == "counter_offer"


def test_reject_requires_known_reason(client: TestClient, analyst: dict) -> None:
    payload = {"action": "reject", "commentForClient": "Отказ по итогам проверки"}
    unknown = client.post("/api/analyst/applications/A-1025/decision",
                          json={**payload, "reasonCode": "unknown"}, headers=analyst)
    assert unknown.status_code == 422
    missing = client.post("/api/analyst/applications/A-1025/decision", json=payload, headers=analyst)
    assert missing.status_code == 422
    rejected = client.post("/api/analyst/applications/A-1025/decision",
                           json={**payload, "reasonCode": "risk_signals"}, headers=analyst)
    assert rejected.json()["decision"]["reasonCode"] == "risk_signals"
