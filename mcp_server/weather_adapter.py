"""Open-Meteo API adapter.

All HTTP access and response normalization lives here so MCP tool functions remain
small and domain-focused. Open-Meteo requires no API key for non-commercial use.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 15
MAX_FORECAST_DAYS = 16


class WeatherAdapterError(RuntimeError):
    """Raised when a location cannot be resolved or Open-Meteo cannot be queried."""


WMO_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snowfall",
    73: "moderate snowfall",
    75: "heavy snowfall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


class OpenMeteoAdapter:
    """Resolve locations and return normalized weather data from Open-Meteo."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.session.get(
                url, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WeatherAdapterError(
                "The weather service is temporarily unavailable. Please try again later."
            ) from exc

        if not isinstance(payload, dict) or payload.get("error"):
            reason = payload.get("reason", "Unexpected response from weather service")
            raise WeatherAdapterError(str(reason))
        return payload

    def resolve_location(self, location: str) -> dict[str, Any]:
        """Resolve a city name into coordinates and a display name."""
        query = location.strip()
        if len(query) < 2:
            raise WeatherAdapterError("Location must contain at least two characters.")

        payload = self._get_json(
            GEOCODING_URL,
            {"name": query, "count": 1, "language": "en", "format": "json"},
        )
        results = payload.get("results") or []
        if not results:
            raise WeatherAdapterError(
                f"Location '{query}' was not found. Add a country or region and try again."
            )

        match = results[0]
        label_parts = [match.get("name"), match.get("admin1"), match.get("country")]
        return {
            "name": ", ".join(str(part) for part in label_parts if part),
            "latitude": float(match["latitude"]),
            "longitude": float(match["longitude"]),
            "timezone": match.get("timezone", "auto"),
        }

    def get_current_weather(self, location: str) -> dict[str, Any]:
        """Return normalized current conditions for a resolved location."""
        place = self.resolve_location(location)
        payload = self._get_json(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "timezone": "auto",
            },
        )
        current = payload.get("current") or {}
        required = {"temperature_2m", "relative_humidity_2m", "weather_code"}
        if not required.issubset(current):
            raise WeatherAdapterError("Current weather data is incomplete.")

        code = int(current["weather_code"])
        return {
            "location": place["name"],
            "observed_at": current.get("time"),
            "temperature_c": current["temperature_2m"],
            "apparent_temperature_c": current.get("apparent_temperature"),
            "humidity_percent": current["relative_humidity_2m"],
            "precipitation_mm": current.get("precipitation", 0),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": code,
            "conditions": WMO_DESCRIPTIONS.get(code, "unknown conditions"),
            "source": "Open-Meteo",
        }

    def get_forecast(self, location: str, days: int = 7) -> dict[str, Any]:
        """Return a normalized daily forecast for 1 to 16 days."""
        if not 1 <= days <= MAX_FORECAST_DAYS:
            raise WeatherAdapterError("Forecast days must be between 1 and 16.")

        place = self.resolve_location(location)
        payload = self._get_json(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max,precipitation_sum,"
                    "wind_speed_10m_max,uv_index_max"
                ),
                "forecast_days": days,
                "timezone": "auto",
            },
        )
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            raise WeatherAdapterError("Forecast data is unavailable for this location.")

        items = []
        for index, day_value in enumerate(dates):
            code = int(daily["weather_code"][index])
            items.append(
                {
                    "date": day_value,
                    "temperature_max_c": daily["temperature_2m_max"][index],
                    "temperature_min_c": daily["temperature_2m_min"][index],
                    "precipitation_probability_percent": daily[
                        "precipitation_probability_max"
                    ][index],
                    "precipitation_sum_mm": daily["precipitation_sum"][index],
                    "wind_speed_max_kmh": daily["wind_speed_10m_max"][index],
                    "uv_index_max": daily["uv_index_max"][index],
                    "weather_code": code,
                    "conditions": WMO_DESCRIPTIONS.get(code, "unknown conditions"),
                }
            )

        return {"location": place["name"], "days": items, "source": "Open-Meteo"}

    def get_forecast_for_date(self, location: str, target_date: str) -> dict[str, Any]:
        """Return one forecast day after validating an ISO date within 16 days."""
        try:
            requested = date.fromisoformat(target_date)
        except ValueError as exc:
            raise WeatherAdapterError("Date must use YYYY-MM-DD format.") from exc

        today = datetime.now().astimezone().date()
        offset = (requested - today).days
        if offset < 0 or offset >= MAX_FORECAST_DAYS:
            raise WeatherAdapterError(
                "Date must be today or within the next 15 days."
            )

        forecast = self.get_forecast(location, offset + 1)
        return {"location": forecast["location"], **forecast["days"][offset]}
