"""create users and search_history tables

Revision ID: 2a26550b39e4
Revises:
Create Date: 2025-05-25 19:44:42.095177

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a26550b39e4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Create 'users' table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("cookie_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Index on cookie_id for lookups
    op.create_index(
        "ix_users_cookie_id",
        "users",
        ["cookie_id"],
        unique=True,
    )

    # 2) Create a 'search_history' table
    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("city_name", sa.String(), nullable=False),
        sa.Column(
            "searched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Indexes for fast queries by user and by city
    op.create_index(
        "ix_search_history_user_id",
        "search_history",
        ["user_id"],
    )
    op.create_index(
        "ix_search_history_city_name",
        "search_history",
        ["city_name"],
    )


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index("ix_search_history_city_name", table_name="search_history")
    op.drop_index("ix_search_history_user_id", table_name="search_history")
    op.drop_table("search_history")

    op.drop_index("ix_users_cookie_id", table_name="users")
    op.drop_table("users")
