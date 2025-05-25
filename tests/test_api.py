import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.services.weather import FORECAST_API_URL, GEOCODING_API_URL


@pytest.mark.asyncio
@respx.mock
async def test_api_suggest_success():
    respx.get(GEOCODING_API_URL).mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "name": "Rome",
                        "country": "Italy",
                        "country_code": "IT",
                        "latitude": 41.9028,
                        "longitude": 12.4964,
                        "admin1": "Lazio",
                        "timezone": "Europe/Rome",
                    }
                ]
            },
        )
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/suggest", params={"query": "Ro"})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["name"] == "Rome"
    assert data[0]["country_code"] == "IT"


@pytest.mark.asyncio
@respx.mock
async def test_api_suggest_error():
    respx.get(GEOCODING_API_URL).mock(return_value=Response(500, text="Oops"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/suggest", params={"query": "Err"})
    assert resp.status_code == 502
    assert "Oops" in resp.json()["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_api_weather_success():
    respx.get(GEOCODING_API_URL).mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "name": "TestCity",
                        "country": "Testland",
                        "country_code": "TL",
                        "latitude": 10.0,
                        "longitude": 20.0,
                        "admin1": "Region",
                        "timezone": "UTC",
                    }
                ]
            },
        )
    )
    respx.get(FORECAST_API_URL).mock(
        return_value=Response(
            200,
            json={
                "latitude": 10.0,
                "longitude": 20.0,
                "generationtime_ms": 0.5,
                "utc_offset_seconds": 0,
                "timezone": "UTC",
                "timezone_abbreviation": "UTC",
                "elevation": 0.0,
                "hourly": {
                    "time": ["2025-05-26T00:00:00Z"],
                    "temperature_2m": [25.0],
                    "weathercode": [0],
                },
            },
        )
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/weather", params={"city": "TestCity"})
    assert resp.status_code == 200
    assert resp.json()["hourly"]["temperature_2m"] == [25.0]


@pytest.mark.asyncio
@respx.mock
async def test_api_weather_not_found():
    respx.get(GEOCODING_API_URL).mock(return_value=Response(200, json={"results": []}))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/weather", params={"city": "Nowhere"})
    assert resp.status_code == 404
    assert "No matching city for 'Nowhere'" in resp.json()["detail"]
