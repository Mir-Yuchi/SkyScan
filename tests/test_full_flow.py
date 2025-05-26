from datetime import datetime, timezone

import pytest
import respx
from httpx import AsyncClient, Response
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.models.search_history import SearchHistory
from app.models.user import User
from app.services.weather import FORECAST_API_URL, GEOCODING_API_URL


@pytest.mark.asyncio
@respx.mock
async def test_full_user_flow(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "SkyScan Weather" in resp.text
        assert "Welcome back" not in resp.text

    respx.get(GEOCODING_API_URL).mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "name": "Alpha",
                        "country": "Aland",
                        "country_code": "AL",
                        "latitude": 10.0,
                        "longitude": 20.0,
                        "admin1": None,
                        "timezone": "UTC",
                    },
                    {
                        "name": "Beta",
                        "country": "Betaland",
                        "country_code": "BE",
                        "latitude": 30.0,
                        "longitude": 40.0,
                        "admin1": None,
                        "timezone": "UTC",
                    },
                ]
            },
        )
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/suggest", params={"query": "A"})
        assert resp.status_code == 200
        data = resp.json()
        assert any(c["name"] == "Alpha" for c in data)
        assert any(c["name"] == "Beta" for c in data)

    # 3. Weather API success: mock geocoding + forecast
    respx.get(GEOCODING_API_URL).mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "name": "Testville",
                        "country": "Testland",
                        "country_code": "TL",
                        "latitude": 1.23,
                        "longitude": 4.56,
                        "admin1": None,
                        "timezone": "UTC",
                    }
                ]
            },
        )
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    respx.get(FORECAST_API_URL).mock(
        return_value=Response(
            200,
            json={
                "latitude": 1.23,
                "longitude": 4.56,
                "generationtime_ms": 0.1,
                "utc_offset_seconds": 0,
                "timezone": "UTC",
                "timezone_abbreviation": "UTC",
                "elevation": 0.0,
                "hourly": {
                    "time": [now_iso],
                    "temperature_2m": [20.0],
                    "weathercode": [0],
                },
            },
        )
    )

    user = User(cookie_id="cookie-1234")
    db_session.add(user)
    await db_session.commit()
    cookies = {"anon_uuid": user.cookie_id}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies=cookies,
    ) as client:
        resp = await client.post("/weather", data={"city": "Testville"})
        assert resp.status_code == 200
        text = resp.text
        assert "Forecast for Testville" in text
        assert "20.0" in text

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies=cookies,
    ) as client:
        resp = await client.get("/api/suggest", params={"query": "T"})
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Testville" in names

    respx.get(GEOCODING_API_URL).mock(return_value=Response(200, json={"results": []}))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/weather", params={"city": "Nowhere"})
        assert resp.status_code == 404
        assert "No matching city for 'Nowhere'" in resp.json()["detail"]
