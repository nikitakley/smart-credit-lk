import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.stubs import store


@pytest.fixture
def client() -> TestClient:
    store.state.reset()
    return TestClient(app)


def login(client: TestClient, account_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"accountId": account_id})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


@pytest.fixture
def prodmarket(client: TestClient) -> dict[str, str]:
    return login(client, "prodmarket")


@pytest.fixture
def analyst(client: TestClient) -> dict[str, str]:
    return login(client, "analyst")
