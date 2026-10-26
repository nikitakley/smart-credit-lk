"""Unit-тесты автомата статусов заявки: без базы и без HTTP, только логика переходов."""

import pytest

from app.config import get_settings
from app.errors import ApiError
from app.schemas.enums import TERMINAL_STATUSES, Actor
from app.schemas.enums import ApplicationStatus as S
from app.services.state_machine import STATUS_LABELS, TRANSITIONS, can_transition, transition
from app.db import models
from app.db.seed import SeedApplication, read_seed

DEMO_APPLICATIONS = read_seed("demo_applications.json", SeedApplication, get_settings().seed_dir)


def make_application(status: S) -> models.Application:
    # Объект существует только в памяти, в базу не сохраняется
    return models.Application(id="A-1", status=status)


def reachable_from(start: S) -> set[S]:
    """Все статусы, в которые можно попасть из start за любое число шагов (обход графа в ширину)."""
    seen, queue = {start}, [start]
    while queue:
        for target in TRANSITIONS[queue.pop(0)]:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def test_every_status_is_described() -> None:
    # Новый статус в enum без правил переходов и подписи — ошибка, ловим сразу
    assert set(TRANSITIONS) == set(S)
    assert set(STATUS_LABELS) == set(S)


def test_allowed_transition_changes_status_and_writes_event() -> None:
    application = make_application(S.draft)

    transition(application, S.submitted, Actor.client, actor_account_id="prodmarket", note="Заявка подана")

    assert application.status == S.submitted
    assert len(application.events) == 1
    event = application.events[0]
    assert (event.status, event.actor, event.actor_account_id) == (S.submitted, Actor.client, "prodmarket")


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.draft, S.approved),  # нельзя перескочить через проверки
        (S.submitted, S.issued),
        (S.approved, S.issued),  # выдача только после подписания
        (S.rejected, S.validation),  # из конечного статуса выхода нет
        (S.issued, S.signing),
    ],
)
def test_forbidden_transition_is_rejected(current: S, target: S) -> None:
    application = make_application(current)

    with pytest.raises(ApiError) as error:
        transition(application, target, Actor.system)

    assert error.value.status_code == 409
    assert error.value.code == "invalid_transition"
    # Заявка не изменилась, лишнее событие не записано
    assert application.status == current
    assert application.events == []


def test_terminal_statuses_have_no_exits() -> None:
    statuses_without_exits = {status for status, targets in TRANSITIONS.items() if not targets}
    assert statuses_without_exits == TERMINAL_STATUSES


def test_every_status_is_reachable_from_draft() -> None:
    # Нет «мёртвых» статусов, в которые заявка никогда не попадёт
    assert reachable_from(S.draft) == set(S)


@pytest.mark.parametrize("status", sorted(set(S) - TERMINAL_STATUSES))
def test_every_status_leads_to_final_result(status: S) -> None:
    # Ни из одного статуса заявка не застрянет навсегда: впереди всегда есть конечный статус
    assert reachable_from(status) & TERMINAL_STATUSES


@pytest.mark.parametrize("seed", DEMO_APPLICATIONS, ids=lambda a: a.id)
def test_demo_history_follows_state_machine(seed: SeedApplication) -> None:
    # Демо-данные тоже обязаны подчиняться автомату: история — допустимый путь из черновика
    path = [S.draft, *(event.status for event in seed.events)]
    for current, target in zip(path, path[1:]):
        assert can_transition(current, target), f"{seed.id}: {current} → {target}"
    assert path[-1] == seed.status
