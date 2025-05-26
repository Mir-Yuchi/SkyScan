from typing import List, Tuple

import httpx
from httpx import RequestError

from app.schemas.weather import City, ForecastResponse, GeocodingResponse

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(Exception):
    """Generic exception for weather service errors."""


async def search_city(
    name: str, max_results: int = 15, client: httpx.AsyncClient | None = None
) -> List[City]:
    """
    Call the Open-Meteo geocoding API to autocomplete city names.
    :raises WeatherServiceError: on HTTP errors (with generic message for JSON errors,
      raw text for non-JSON), or on network/request errors.
    """
    own_client = client or httpx.AsyncClient(timeout=5.0)
    try:
        resp = await own_client.get(
            GEOCODING_API_URL, params={"name": name, "count": max_results}
        )
        if resp.status_code >= 400:
            try:
                resp.json()
            except ValueError:
                raise WeatherServiceError(resp.text)
            else:
                raise WeatherServiceError(
                    f"Geocoding API returned HTTP {resp.status_code}"
                )

        data = GeocodingResponse.model_validate(resp.json())
        return data.results

    except WeatherServiceError:
        raise
    except RequestError as e:
        raise WeatherServiceError(f"Error requesting Geocoding API: {e}") from e
    except Exception as e:
        raise WeatherServiceError(f"Geocoding failed: {e}") from e
    finally:
        if client is None:
            await own_client.aclose()


async def get_forecast(lat: float, lon: float) -> ForecastResponse:
    """
    Call the Open-Meteo Forecast API for hourly temperature and weather code.
    :raises WeatherServiceError: on HTTP errors (generic for JSON, raw text otherwise),
      or on network/request errors.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,weathercode",
        "current_weather": True,
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(FORECAST_API_URL, params=params)
        except RequestError as e:
            raise WeatherServiceError(f"Error requesting Forecast API: {e}") from e

        if resp.status_code >= 400:
            try:
                resp.json()
            except ValueError:
                raise WeatherServiceError(resp.text)
            else:
                raise WeatherServiceError(
                    f"Forecast API returned HTTP {resp.status_code}"
                )

        return ForecastResponse.model_validate(resp.json())


async def fetch_weather_by_city(
    city_name: str, client: httpx.AsyncClient | None = None
) -> Tuple[City, ForecastResponse]:
    """
    Autocomplete a city name, pick the first match,
    fetch its forecast and return both.
    :raises WeatherServiceError: if no match or underlying API errors.
    """
    cities = await search_city(city_name, max_results=1, client=client)
    if not cities:
        raise WeatherServiceError(f"No matching city for '{city_name}'")

    city = cities[0]
    forecast = await get_forecast(city.latitude, city.longitude)
    return city, forecast
