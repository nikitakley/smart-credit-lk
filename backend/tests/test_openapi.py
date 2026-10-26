"""Документация API не отстаёт от кода."""

import json
import re
from pathlib import Path

from app.errors import CONFLICT_CODES
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]
OPENAPI_FILE = BACKEND_DIR.parent / "docs" / "api" / "openapi.json"


def test_openapi_file_is_up_to_date() -> None:
    # Фронтенд и документация опираются на docs/api/openapi.json, а не на код. Если тест упал:
    #   uv run python scripts/export_openapi.py   — и закоммитить файл вместе с изменением
    saved = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(app.openapi(), ensure_ascii=False))
    assert saved == actual, "docs/api/openapi.json устарел: uv run python scripts/export_openapi.py"


def test_conflict_codes_are_documented() -> None:
    # Каждый код 409, который выдаёт сервис, описан в CONFLICT_CODES (и наоборот — нет «мёртвых» описаний)
    source = "\n".join(p.read_text(encoding="utf-8") for p in (BACKEND_DIR / "app").rglob("*.py"))
    used = set(re.findall(r'conflict\(\s*"(\w+)"', source))
    assert used == set(CONFLICT_CODES)
