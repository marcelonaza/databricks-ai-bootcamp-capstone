"""FastMCP weather server for Databricks Apps."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP

from weather_adapter import OpenMeteoAdapter, WeatherAdapterError


mcp = FastMCP("weather-prediction-mcp")
weather = OpenMeteoAdapter()


def _safe_call(operation: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "data": operation(*args, **kwargs)}
    except WeatherAdapterError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool
def get_current_weather(location: str) -> dict[str, Any]:
    """Get current weather conditions for a location.

    Args:
        location: City or place name. Include country/region when ambiguous.

    Returns:
        A clean dictionary with temperature, apparent temperature, humidity,
        precipitation, wind, conditions, observation time, and source. Returns
        ``ok=false`` with a user-safe error when resolution or API access fails.
    """
    return _safe_call(weather.get_current_weather, location)


@mcp.tool
def get_forecast(location: str, days: int = 7) -> dict[str, Any]:
    """Get a multi-day daily weather forecast.

    Args:
        location: City or place name. Include country/region when ambiguous.
        days: Number of forecast days, from 1 through 16.

    Returns:
        Daily high/low temperatures, maximum precipitation probability,
        precipitation amount, maximum wind, UV index, and conditions. Returns
        ``ok=false`` with a user-safe error for invalid input or API failure.
    """
    return _safe_call(weather.get_forecast, location, days)


@mcp.tool
def get_weather_recommendation(location: str, date: str) -> dict[str, Any]:
    """Generate practical advice from a forecast using explicit safety rules.

    The derived rules recommend an umbrella at precipitation probability >=40%,
    a jacket when the daily minimum is <12 C, sun protection when UV >=6, and
    wind caution when maximum wind is >=40 km/h. Multiple rules may apply.

    Args:
        location: City or place name. Include country/region when ambiguous.
        date: Forecast date in YYYY-MM-DD format, today through 15 days ahead.

    Returns:
        The forecast values, triggered rule thresholds, and an explained list of
        recommendations. Returns ``ok=false`` with a clean error for unsupported
        dates, unknown locations, or service failure.
    """
    result = _safe_call(weather.get_forecast_for_date, location, date)
    if not result["ok"]:
        return result

    day = result["data"]
    advice = []
    triggered = []
    rain_probability = day.get("precipitation_probability_percent") or 0
    minimum = day.get("temperature_min_c")
    uv_index = day.get("uv_index_max") or 0
    wind = day.get("wind_speed_max_kmh") or 0

    if rain_probability >= 40:
        advice.append("Bring an umbrella or waterproof layer.")
        triggered.append("precipitation_probability_percent >= 40")
    if minimum is not None and minimum < 12:
        advice.append("Bring a jacket for the colder part of the day.")
        triggered.append("temperature_min_c < 12")
    if uv_index >= 6:
        advice.append("Use sunscreen, sunglasses, and seek shade around midday.")
        triggered.append("uv_index_max >= 6")
    if wind >= 40:
        advice.append("Use caution with exposed outdoor activities due to strong wind.")
        triggered.append("wind_speed_max_kmh >= 40")
    if not advice:
        advice.append("No special weather precautions are indicated by these rules.")
        triggered.append("no threshold triggered")

    return {
        "ok": True,
        "data": {
            "location": day["location"],
            "date": day["date"],
            "forecast": day,
            "recommendations": advice,
            "triggered_rules": triggered,
            "source": "Open-Meteo",
        },
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.getenv("DATABRICKS_APP_PORT", "8000")),
    )
