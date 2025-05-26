from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models.search_history import SearchHistory
from app.services.weather import WeatherServiceError, fetch_weather_by_city

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request, session: AsyncSession = Depends(get_async_session)
):
    """
    Root endpoint to render the main page with recent search history.
        :param request:
        :param session:
        :return: HTMLResponse with the main page.
    """
    stmt = (
        select(SearchHistory.city_name)
        .filter_by(user_id=request.state.user.id)
        .order_by(desc(SearchHistory.search_at))
        .limit(5)
    )
    rows = await session.execute(stmt)
    recent_cities = [r[0] for r in rows.all()]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "city": None,
            "recent_cities": recent_cities,
            "preview": [],
            "full": [],
        },
    )


@router.post("/weather", response_class=HTMLResponse)
async def post_weather(
    request: Request,
    city: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Fetch weather for a given city and render the results.
        :param request:
        :param city:
        :param session:
        :return:
    """
    try:
        city_obj, forecast = await fetch_weather_by_city(city)
    except WeatherServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))

    session.add(SearchHistory(user_id=request.state.user.id, city_name=city_obj.name))
    await session.commit()

    stmt = (
        select(SearchHistory.city_name)
        .filter_by(user_id=request.state.user.id)
        .order_by(desc(SearchHistory.search_at))
        .limit(5)
    )
    rows = await session.execute(stmt)
    recent_cities = [r[0] for r in rows.all()]

    tz = ZoneInfo(city_obj.timezone)
    now_local = datetime.now(tz)

    entries = list(zip(forecast.hourly.time, forecast.hourly.temperature_2m))
    future_entries = []
    for t, temp in entries:
        t_local = t.astimezone(tz) if t.tzinfo else t.replace(tzinfo=tz)
        if t_local >= now_local:
            future_entries.append((t_local, temp))

    if not future_entries:
        future_entries = entries

    preview = future_entries[:6]
    full = future_entries

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "city": city_obj,
            "recent_cities": recent_cities,
            "preview": preview,
            "full": full,
        },
    )
