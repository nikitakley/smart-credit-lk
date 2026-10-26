"""Документация симулятора не отстаёт от кода."""

import json
from pathlib import Path

from simulator.main import app

OPENAPI_FILE = Path(__file__).resolve().parents[2] / "docs" / "api" / "mocks-openapi.json"


def test_openapi_file_is_up_to_date() -> None:
    # Если тест упал: uv run python scripts/export_openapi.py — и закоммитить файл вместе с изменением
    saved = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(app.openapi(), ensure_ascii=False))
    assert saved == actual, "docs/api/mocks-openapi.json устарел: uv run python scripts/export_openapi.py"
