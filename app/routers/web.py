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
    Landing page:
     - empty form
     - up to 5 recent cities as quick-links
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
            "forecast": None,
            "city": None,
            "recent_cities": recent_cities,
        },
    )


@router.post("/weather", response_class=HTMLResponse)
async def post_weather(
    request: Request,
    city: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Fetch weather, persist the search, and re-render with results.
    """
    try:
        city_obj, forecast = await fetch_weather_by_city(city)
    except WeatherServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))

    session.add(SearchHistory(user_id=request.state.user.id, city_name=city_obj.name))
    await session.commit()

    # Re-fetch recents so the panel updates immediately
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
            "forecast": forecast,
            "city": city_obj,
            "recent_cities": recent_cities,
        },
    )
