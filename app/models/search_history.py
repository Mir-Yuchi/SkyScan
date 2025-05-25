from datetime import datetime, timezone

from sqlalchemy import DATETIME, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class SearchHistory(Base):
    """Records each time a user looked up the weather forecast for a given city."""

    __tablename__ = "search_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="Primary key for the search history record",
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key linking back to users.id",
    )

    city_name = Column(
        String, nullable=False, index=True, comment="Name of the city that was searched"
    )

    search_at = Column(
        DATETIME(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when the search was made",
    )

    user = relationship("User", back_populates="search_history")
