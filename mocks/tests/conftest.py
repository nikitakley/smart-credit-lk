import os

# Без задержек: тесты должны быть быстрыми. Выставляется до импорта симулятора — настройки читаются при импорте.
os.environ["MOCK_LATENCY_MIN_MS"] = "0"
os.environ["MOCK_LATENCY_MAX_MS"] = "0"
os.environ["MOCK_FAILURE_RATE"] = "0"
os.environ["MOCKS_API_KEY"] = "test-key"

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from simulator.faults import get_faults
from simulator.journal import get_journal
from simulator.main import app

KEY = {"X-Api-Key": "test-key"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Поведение источников хранится в памяти процесса — сбрасываем, чтобы тесты не влияли друг на друга
    get_faults().reset()
    get_journal().clear()
    with TestClient(app) as test_client:
        yield test_client
