import httpx
import pytest
import respx
from httpx import Response

from app.schemas.weather import City, ForecastResponse
from app.services.weather import (
    FORECAST_API_URL,
    GEOCODING_API_URL,
    WeatherServiceError,
    fetch_weather_by_city,
    get_forecast,
    search_city,
)


@pytest.mark.asyncio
@respx.mock
async def test_search_city_success():
    mock_payload = {
        "results": [
            {
                "name": "Moscow",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "admin1": None,
                "country_code": "RU",
                "country": "Russia",
                "timezone": "Europe/Moscow",
            }
        ]
    }
    respx.get(GEOCODING_API_URL).mock(return_value=Response(200, json=mock_payload))

    cities = await search_city("Moscow")
    assert isinstance(cities, list)
    assert len(cities) == 1
    city = cities[0]
    assert isinstance(city, City)
    assert city.name == "Moscow"
    assert city.latitude == pytest.approx(55.7558)


@pytest.mark.asyncio
@respx.mock
async def test_search_city_http_error():
    respx.get(GEOCODING_API_URL).mock(
        return_value=Response(500, json={"error": "server error"})
    )
    with pytest.raises(WeatherServiceError) as excinfo:
        await search_city("Xyz")
    assert "Geocoding API returned HTTP 500" in str(excinfo.value)


@pytest.mark.asyncio
async def test_search_city_request_error(monkeypatch):
    async def _raise(*args, **kwargs):
        raise httpx.RequestError("Network down")

    monkeypatch.setattr(httpx.AsyncClient, "get", _raise)
    with pytest.raises(WeatherServiceError) as excinfo:
        await search_city("Xyz")
    assert "Error requesting Geocoding API" in str(excinfo.value)


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_success():
    lat, lon = 55.7558, 37.6173
    mock_payload = {
        "latitude": lat,
        "longitude": lon,
        "generationtime_ms": 1.23,
        "utc_offset_seconds": 3600,
        "timezone": "Europe/Moscow",
        "timezone_abbreviation": "MSK",
        "elevation": 100.0,
        "hourly": {
            "time": ["2023-10-01T00:00:00Z", "2023-10-01T01:00:00Z"],
            "temperature_2m": [15.0, 14.5],
            "weathercode": [0, 1],
        },
    }
    respx.get(FORECAST_API_URL).mock(return_value=Response(200, json=mock_payload))

    forecast = await get_forecast(lat, lon)
    assert isinstance(forecast, ForecastResponse)
    assert forecast.latitude == pytest.approx(lat)
    assert forecast.longitude == pytest.approx(lon)
    data = forecast.model_dump()
    assert data["hourly"]["temperature_2m"] == [15.0, 14.5]
    assert data["hourly"]["weathercode"] == [0, 1]


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_http_error():
    respx.get(FORECAST_API_URL).mock(
        return_value=Response(404, json={"error": "not found"})
    )

    with pytest.raises(WeatherServiceError) as excinfo:
        await get_forecast(0.0, 0.0)
    assert "Forecast API returned HTTP 404" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_forecast_request_error(monkeypatch):
    async def _raise(*args, **kwargs):
        raise httpx.RequestError("network down")

    monkeypatch.setattr(httpx.AsyncClient, "get", _raise)

    with pytest.raises(WeatherServiceError) as excinfo:
        await get_forecast(0.0, 0.0)
    assert "Error requesting Forecast API" in str(excinfo.value)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_weather_by_city_happy_path():
    geo_payload = {
        "results": [
            {
                "name": "Testville",
                "country": "Testland",
                "country_code": "TL",
                "latitude": 12.34,
                "longitude": 56.78,
                "admin1": "Region",
                "timezone": "UTC",
            }
        ]
    }
    respx.get(GEOCODING_API_URL).mock(return_value=Response(200, json=geo_payload))

    forecast_payload = {
        "latitude": 12.34,
        "longitude": 56.78,
        "generationtime_ms": 0.99,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "timezone_abbreviation": "UTC",
        "elevation": 50.0,
        "hourly": {
            "time": ["2025-05-26T00:00:00Z"],
            "temperature_2m": [20.0],
            "weathercode": [0],
        },
    }
    respx.get(FORECAST_API_URL).mock(return_value=Response(200, json=forecast_payload))

    city, forecast = await fetch_weather_by_city("Testville")
    assert isinstance(city, City)
    assert city.name == "Testville"
    assert isinstance(forecast, ForecastResponse)
    assert forecast.hourly.temperature_2m == [20.0]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_weather_by_city_no_match():
    respx.get(GEOCODING_API_URL).mock(return_value=Response(200, json={"results": []}))

    with pytest.raises(WeatherServiceError) as excinfo:
        await fetch_weather_by_city("UnknownCity")
    assert "No matching city for 'UnknownCity'" in str(excinfo.value)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_weather_by_city_geocoding_error():
    respx.get(GEOCODING_API_URL).mock(return_value=Response(500, text="Error"))

    with pytest.raises(WeatherServiceError):
        await fetch_weather_by_city("ErrorTown")
