"""Вид события в истории заявки: смена статуса или действие без смены статуса

Revision ID: 356274599dbd
Revises: ab458cc529f5
Create Date: 2026-10-26 10:50:24.617471+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '356274599dbd'
down_revision: Union[str, Sequence[str], None] = 'ab458cc529f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Все уже записанные события — смены статуса: server_default проставит им status_changed,
    # поэтому колонку можно сразу сделать NOT NULL без отдельного UPDATE
    op.add_column(
        'application_events',
        sa.Column(
            'kind',
            sa.Enum('status_changed', 'checks_refreshed', name='eventkind',
                    native_enum=False, create_constraint=True, length=32),
            server_default='status_changed',
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Вместе с колонкой удаляется и её CHECK-ограничение
    op.drop_column('application_events', 'kind')
