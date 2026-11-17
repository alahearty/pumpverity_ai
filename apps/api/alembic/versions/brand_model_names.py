"""brand synthetic model display names

Revision ID: b7f0c2a4d910
Revises: 6ab8b0723c85
Create Date: 2026-11-17
"""

from alembic import op

revision = "b7f0c2a4d910"
down_revision = "6ab8b0723c85"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE model_versions SET name = replace(name, 'PetroSense', 'PUMPVERITY') "
        "WHERE name LIKE 'PetroSense%'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE model_versions SET name = replace(name, 'PUMPVERITY', 'PetroSense') "
        "WHERE name LIKE 'PUMPVERITY%'"
    )
