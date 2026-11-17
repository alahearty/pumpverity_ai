"""stage 4 linear json runtime

Revision ID: cc4e2d9b7f12
Revises: bb5d543b303c
Create Date: 2026-11-16 17:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "cc4e2d9b7f12"
down_revision: str | None = "bb5d543b303c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = ("ONNX", "SKLEARN", "TFLITE", "BASELINE")
_NEW = (*_OLD, "LINEAR_JSON")


def upgrade() -> None:
    with op.batch_alter_table("model_versions", schema=None) as batch_op:
        batch_op.alter_column(
            "runtime",
            existing_type=sa.Enum(
                *_OLD,
                name="model_runtime",
                native_enum=False,
                create_constraint=True,
                length=24,
            ),
            type_=sa.Enum(
                *_NEW,
                name="model_runtime",
                native_enum=False,
                create_constraint=True,
                length=24,
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("model_versions", schema=None) as batch_op:
        batch_op.alter_column(
            "runtime",
            existing_type=sa.Enum(
                *_NEW,
                name="model_runtime",
                native_enum=False,
                create_constraint=True,
                length=24,
            ),
            type_=sa.Enum(
                *_OLD,
                name="model_runtime",
                native_enum=False,
                create_constraint=True,
                length=24,
            ),
            existing_nullable=False,
        )
