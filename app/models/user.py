import uuid
from datetime import datetime, timezone

from sqlalchemy import DATETIME, Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """A website user, identified by a UUID stored in their cookie"""

    __tablename__ = "users"

    id = Column(
        Integer, primary_key=True, index=True, comment="Auto-incrementing user ID"
    )

    cookie_id = Column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        comment="UUID stored in the user's cookie",
    )

    created_at = Column(
        DATETIME(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when the user record was created",
    )

    search_history = relationship(
        "SearchHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
