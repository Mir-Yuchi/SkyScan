from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.search_history import SearchHistory
from app.models.user import User


@pytest.mark.asyncio
async def test_history_and_stats(db_session):
    # 1) Create two users in the test DB
    user1 = User(cookie_id="user-uuid-1")
    user2 = User(cookie_id="user-uuid-2")
    db_session.add_all([user1, user2])
    await db_session.commit()

    # 2) Insert search records for both users
    now = datetime.now(timezone.utc)
    records = [
        SearchHistory(
            user_id=user1.id, city_name="CityA", search_at=now - timedelta(minutes=2)
        ),
        SearchHistory(
            user_id=user1.id, city_name="CityB", search_at=now - timedelta(minutes=1)
        ),
        SearchHistory(user_id=user2.id, city_name="CityA", search_at=now),
    ]
    db_session.add_all(records)
    await db_session.commit()

    # 3) Fetch /api/history for user1 (via cookie)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"anon_uuid": user1.cookie_id},
    ) as client:
        resp = await client.get("/api/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    assert history[0]["city_name"] == "CityB"
    assert history[1]["city_name"] == "CityA"

    # 4) Fetch /api/stats
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/stats")
    assert resp.status_code == 200
    stats = {item["city_name"]: item["count"] for item in resp.json()}
    assert stats["CityA"] == 2
    assert stats["CityB"] == 1
