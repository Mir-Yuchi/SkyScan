from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models.search_history import SearchHistory
from app.schemas.history import HistoryItem, StatsItem
from app.schemas.weather import City as CitySchema
from app.schemas.weather import ForecastResponse
from app.services.weather import WeatherServiceError, fetch_weather_by_city, search_city

router = APIRouter(tags=["weather"])


@router.get("/health", tags=["api"])
async def health_check():
    return {"status": "ok"}


@router.get("/suggest", response_model=list[CitySchema])
async def suggest_city(
    request: Request,
    query: str = Query(..., min_length=1, description="City name to autocomplete"),
    limit: int = Query(15, ge=1, le=50, description="Max suggestions to return"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Blended autocomplete:
      1) Top-5 history prefix matches
      2) Top-5 history substring matches
      3) Up to `limit` external suggestions
      → merge, dedupe, return up to `limit`
    """
    user_id = request.state.user.id

    prefix_stmt = (
        select(SearchHistory.city_name, func.count().label("freq"))
        .filter(SearchHistory.user_id == user_id)
        .filter(SearchHistory.city_name.ilike(f"{query}%"))
        .group_by(SearchHistory.city_name)
        .order_by(desc("freq"))
        .limit(5)
    )
    prefix_rows = (await session.execute(prefix_stmt)).all()
    prefix_sugs = [CitySchema(name=name) for name, freq in prefix_rows]
    prefix_names = {name for name, _ in prefix_rows}

    substr_stmt = (
        select(SearchHistory.city_name, func.count().label("freq"))
        .filter(SearchHistory.user_id == user_id)
        .filter(SearchHistory.city_name.ilike(f"%{query}%"))
        .filter(not_(SearchHistory.city_name.in_(prefix_names)))
        .group_by(SearchHistory.city_name)
        .order_by(desc("freq"))
        .limit(5)
    )
    substr_rows = (await session.execute(substr_stmt)).all()
    substr_sugs = [CitySchema(name=name) for name, freq in substr_rows]

    try:
        api_sugs = await search_city(query, max_results=limit)
    except WeatherServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    seen = set()
    merged: list[CitySchema] = []
    for src in (*prefix_sugs, *substr_sugs, *api_sugs):
        if src.name not in seen:
            seen.add(src.name)
            merged.append(src)
        if len(merged) >= limit:
            break

    return merged


@router.get("/weather", response_model=ForecastResponse, tags=["weather"])
async def get_weather(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    city: str = Query(..., min_length=1, description="City name to fetch weather for"),
):
    """
    Fetch weather for a given city name and log the search.
    """
    try:
        city_obj, forecast = await fetch_weather_by_city(city)
        session.add(
            SearchHistory(user_id=request.state.user.id, city_name=city_obj.name)
        )
        await session.commit()
        return forecast
    except WeatherServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history", response_model=list[HistoryItem], tags=["weather"])
async def get_history(
    request: Request, session: AsyncSession = Depends(get_async_session)
):
    """
    Return the search history for the current anonymous user, the most recent first.
    """
    stmt = (
        select(SearchHistory)
        .filter_by(user_id=request.state.user.id)
        .order_by(SearchHistory.search_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/stats", response_model=list[StatsItem], tags=["weather"])
async def get_stats(session: AsyncSession = Depends(get_async_session)):
    """
    Return global counts of how many times each city has been searched.
    """
    stmt = select(SearchHistory.city_name, func.count().label("count")).group_by(
        SearchHistory.city_name
    )
    rows = (await session.execute(stmt)).all()
    return [StatsItem(city_name=city, count=count) for city, count in rows]


@router.get("/user/stats", response_model=list[StatsItem])
async def get_user_stats(
    request: Request, session: AsyncSession = Depends(get_async_session)
):
    """
    How many times YOU have searched each city.
    """
    stmt = (
        select(SearchHistory.city_name, func.count().label("count"))
        .filter(SearchHistory.user_id == request.state.user.id)
        .group_by(SearchHistory.city_name)
    )
    rows = (await session.execute(stmt)).all()
    return [StatsItem(city_name=city, count=count) for city, count in rows]
