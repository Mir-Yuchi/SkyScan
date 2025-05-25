from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.weather import WeatherServiceError, fetch_weather_by_city

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, tags=["web"])
async def read_root(request: Request):
    """
    Render the landing page with an empty form.
    """
    return templates.TemplateResponse(
        "index.html", {"request": request, "forecast": None, "city": None}
    )


@router.post("/weather", response_class=HTMLResponse, tags=["web"])
async def post_weather(request: Request, city: str = Form(...)):
    """
    Handle form submission, fetch weather, and re-render template with results.
    """
    try:
        city_obj, forecast = await fetch_weather_by_city(city)
    except WeatherServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "forecast": forecast, "city": city_obj},
    )
