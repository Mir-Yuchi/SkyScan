from datetime import datetime

from pydantic import BaseModel, Field

__all__ = [
    "City",
    "GeocodingResponse",
    "ForecastHourly",
    "ForecastResponse",
]


class City(BaseModel):
    """
    One autocomplete result from the Geocoding API.
    """

    name: str = Field(..., description="City name, e.g. 'Moscow'")
    country: str | None = Field(None, description="Country name, e.g. 'Russia'")
    country_code: str | None = Field(
        None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2 code"
    )
    latitude: float | None = Field(None, description="Latitude in decimal degrees")
    longitude: float | None = Field(None, description="Longitude in decimal degrees")
    admin1: str | None = Field(
        None, description="State / region / admin1 subdivision, if available"
    )
    timezone: str | None = Field(
        None, description="IANA timezone name, e.g. 'Europe/Moscow'"
    )
    search_count: int | None = Field(
        None, description="Number of times this city was searched (history)"
    )

    model_config = {"populate_by_name": True}


class GeocodingResponse(BaseModel):
    """
    Response wrapper for the geocoding (autocomplete) endpoint.
    """

    results: list[City] = Field(
        ..., description="List of matching cities (up to max. 10)"
    )


class ForecastHourly(BaseModel):
    """
    The hourly forecast data arrays.
    All lists are the same length, aligned by index.
    """

    time: list[datetime] = Field(
        ..., description="List of ISO‐8601 timestamps in the requested timezone"
    )
    temperature_2m: list[float] = Field(
        ..., description="List of air temperatures at 2 m above ground (°C)"
    )
    weathercode: list[int] = Field(
        ..., description="List of weather condition codes (Open‐Meteo schema)"
    )

    model_config = {"populate_by_name": True}


class ForecastResponse(BaseModel):
    """
    Full forecast response, including location metadata and hourly arrays.
    """

    latitude: float = Field(..., description="Latitude of the forecast point")
    longitude: float = Field(..., description="Longitude of the forecast point")
    generationtime_ms: float = Field(
        ..., description="Time (ms) the server took to generate this forecast"
    )
    utc_offset_seconds: int = Field(
        ..., description="Offset from UTC in seconds for the reported timestamps"
    )
    timezone: str = Field(..., description="IANA timezone name")
    timezone_abbreviation: str = Field(
        ..., description="Short timezone abbreviation, e.g. 'MSK'"
    )
    elevation: float | None = Field(
        None, description="Elevation above sea level in meters (optional)"
    )
    hourly: ForecastHourly = Field(..., description="Hourly weather data arrays")
