from datetime import datetime

from pydantic import BaseModel


class HistoryItem(BaseModel):
    """
    Represents a single history item with a city name and search timestamp.
    """

    city_name: str
    search_at: datetime

    model_config = {"from_attributes": True}


class StatsItem(BaseModel):
    """
    Represents a statistics item with a city name and count of searches.
    """

    city_name: str
    count: int
