from datetime import datetime, timezone

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select

from app.main import app
from app.models.search_history import SearchHistory
from app.models.user import User

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


@pytest.mark.asyncio
async def test_read_root_no_history(db_session):
    """
    GET / with no prior history for a new user should NOT show the 'See weather for ...' prompt.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "See weather for" not in html


@pytest.mark.asyncio
async def test_read_root_with_history(db_session):
    """
    If the user has a SearchHistory entry, GET / should render
    a button to 'See weather for <last_city>'.
    """
    # 1) create a user and one search record
    user = User(cookie_id="uuid-1234")
    db_session.add(user)
    await db_session.commit()

    last_city = "Springfield"
    history = SearchHistory(
        user_id=user.id,
        city_name=last_city,
        search_at=datetime.now(timezone.utc),
    )
    db_session.add(history)
    await db_session.commit()

    # 2) request "/" with that user's cookie
    cookies = {"anon_uuid": user.cookie_id}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", cookies=cookies
    ) as client:
        resp = await client.get("/")
    assert resp.status_code == 200

    html = resp.text
    assert f"See weather for {last_city}" in html
    # also verify the hidden input carries the correct value
    assert f'<input type="hidden" name="city" value="{last_city}"' in html


@pytest.mark.asyncio
@respx.mock
async def test_post_weather_logs_and_renders(db_session):
    """
    POST /weather should:
     - call the external APIs (mocked here)
     - render the forecast in the HTML
     - persist a SearchHistory entry for the user
    """
    # 1) mock the geocoding + forecast APIs
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
                    "time": ["2025-05-26T00:00:00Z"],
                    "temperature_2m": [15.0],
                    "weathercode": [0],
                },
            },
        )
    )

    # 2) create user
    user = User(cookie_id="uuid-5678")
    db_session.add(user)
    await db_session.commit()

    # 3) POST /weather
    cookies = {"anon_uuid": user.cookie_id}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", cookies=cookies
    ) as client:
        resp = await client.post("/weather", data={"city": "Testville"})
    assert resp.status_code == 200

    html = resp.text
    assert "Forecast for Testville" in html
    assert "15.0°C" in html or "15.0" in html  # confirms the temperature shows up

    # 4) record was persisted
    result = await db_session.execute(select(SearchHistory).filter_by(user_id=user.id))
    records = result.scalars().all()
    assert len(records) == 1
    assert records[0].city_name == "Testville"
