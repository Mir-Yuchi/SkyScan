# app/routers/api.py
from fastapi import APIRouter, HTTPException, Query

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
    city: str = Query(..., min_length=1, description="City name to fetch weather for")
):
    """
    Fetch weather for a given city name.
    """
    try:
        _, forecast = await fetch_weather_by_city(city)
        return forecast
    except WeatherServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
