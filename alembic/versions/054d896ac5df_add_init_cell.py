"""Add init cell

Revision ID: 054d896ac5df
Revises: da14d40e6815
Create Date: 2022-05-08 15:00:22.717282

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '054d896ac5df'
down_revision = 'da14d40e6815'
branch_labels = None
depends_on = None


def upgrade():
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(only=("cells",))
    op.bulk_insert(
        sa.Table('cells', meta),
        [
            {"order_id": None, "is_open": True},
        ],
    )
    op.execute("DELETE FROM user_roles WHERE id = 3")


def downgrade():
    op.execute("DELETE FROM cells")
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(only=("user_roles",))
    op.bulk_insert(
        sa.Table('user_roles', meta),
        [
            {"id": 3, "name": "service"},
        ],
    )
