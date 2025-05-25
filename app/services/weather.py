from typing import List, Tuple

import httpx

from app.schemas.weather import City, ForecastResponse, GeocodingResponse

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(Exception):
    """Generic exception for weather service errors."""


async def search_city(q: str) -> List[City]:
    """
    Call the Open-Meteo geocoding API to autocomplete city names.
    :param q: partial or full city name
    :return: A list of City objects (up to 10).
    :raises WeatherServiceError: On HTTP errors or timeouts.
    """
    params = {"name": q, "count": 10}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GEOCODING_API_URL, params=params, timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            resp = e.response
            # If the body is JSON, hide it and report only the status code;
            # if it's plain text, propagate that.
            try:
                resp.json()
                err_msg = f"Geocoding API returned HTTP {resp.status_code}"
            except ValueError:
                err_msg = resp.text or f"Geocoding API returned HTTP {resp.status_code}"
            raise WeatherServiceError(err_msg) from e
        except httpx.RequestError as e:
            raise WeatherServiceError(f"Error requesting Geocoding API: {e}") from e

        data = response.json()
        result = GeocodingResponse.model_validate(data)
        return result.results


async def get_forecast(lat: float, lon: float) -> ForecastResponse:
    """
    Call the Open-Meteo Forecast API for hourly temperature and weather code.
    :param lat: Latitude of the location
    :param lon: Longitude of the location
    :return: A ForecastResponse object containing metadata and hourly forecast data.
    :raises WeatherServiceError: On HTTP errors or timeouts.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,weathercode",
        "timezone": "auto",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(FORECAST_API_URL, params=params, timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise WeatherServiceError(
                f"Forecast API returned HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise WeatherServiceError(f"Error requesting Forecast API: {e}") from e

        data = response.json()
        return ForecastResponse.model_validate(data)


async def fetch_weather_by_city(q: str) -> Tuple[City, ForecastResponse]:
    """
    Autocomplete a city name, pick the first match,
    fetch its forecast and return both.
    :param q: City name to look up
    :return: Tuple of (City, ForecastResponse)
    :raises WeatherServiceError: if no city matches or underlying API errors
    """
    cities = await search_city(q)
    if not cities:
        raise WeatherServiceError(f"No matching city for '{q}'")

    city = cities[0]
    forecast = await get_forecast(city.latitude, city.longitude)
    return city, forecast
