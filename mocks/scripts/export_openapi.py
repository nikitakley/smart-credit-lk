"""Экспорт спецификации OpenAPI симулятора в docs/api/mocks-openapi.json.

Запуск из папки mocks:  uv run python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

MOCKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MOCKS_DIR))

from simulator.main import app  # noqa: E402

target = MOCKS_DIR.parent / "docs" / "api" / "mocks-openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"OpenAPI симулятора сохранён: {target}")
