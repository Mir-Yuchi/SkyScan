from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models.search_history import SearchHistory
from app.schemas.history import HistoryItem, StatsItem
from app.schemas.weather import City as CitySchema
from app.schemas.weather import ForecastResponse
from app.services.weather import WeatherServiceError, fetch_weather_by_city, search_city

router = APIRouter()


@router.get("/health", tags=["api"])
async def health_check():
    return {"status": "ok"}


@router.get("/suggest", response_model=list[CitySchema], tags=["weather"])
async def suggest_city(
    query: str = Query(..., min_length=1, description="City name to autocomplete")
):
    """
    Autocomplete city names.
    """
    try:
        return await search_city(query)
    except WeatherServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))


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
