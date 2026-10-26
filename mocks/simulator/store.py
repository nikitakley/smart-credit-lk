"""Синтетические данные источников: читаются из data/*.json один раз и проверяются моделями."""

import json
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from simulator.config import get_settings
from simulator.models import EgrRecord, NbkiRecord, PbRecord

T = TypeVar("T", bound=BaseModel)


def _load(path: Path, model: type[T]) -> dict[str, T]:
    items = [model.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]
    by_inn = {item.inn: item for item in items}  # type: ignore[attr-defined]
    if len(by_inn) != len(items):
        raise ValueError(f"{path.name}: повторяющиеся ИНН")
    return by_inn


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.egr = _load(data_dir / "egr.json", EgrRecord)
        self.nbki = _load(data_dir / "nbki.json", NbkiRecord)
        self.pb = _load(data_dir / "pb.json", PbRecord)


@lru_cache
def get_store() -> Store:
    return Store(get_settings().mock_data_dir)
