from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from mcp_server.weather_adapter import OpenMeteoAdapter, WeatherAdapterError


def response(payload, status_code=200):
    item = Mock()
    item.json.return_value = payload
    item.raise_for_status.return_value = None
    if status_code >= 400:
        item.raise_for_status.side_effect = requests.HTTPError("failure")
    return item


def test_current_weather_is_normalized():
    session = Mock()
    session.get.side_effect = [
        response({"results": [{"name": "Lisbon", "country": "Portugal", "latitude": 38.72, "longitude": -9.14}]}),
        response({"current": {"time": "2026-08-09T12:00", "temperature_2m": 24.2, "relative_humidity_2m": 55, "apparent_temperature": 25.0, "precipitation": 0.0, "weather_code": 1, "wind_speed_10m": 12.0}}),
    ]
    result = OpenMeteoAdapter(session).get_current_weather("Lisbon")
    assert result["location"] == "Lisbon, Portugal"
    assert result["conditions"] == "mainly clear"
    assert result["temperature_c"] == 24.2


def test_unknown_location_returns_clean_error():
    session = Mock()
    session.get.return_value = response({"results": []})
    with pytest.raises(WeatherAdapterError, match="was not found"):
        OpenMeteoAdapter(session).resolve_location("NotARealPlace")


def test_api_failure_is_wrapped():
    session = Mock()
    session.get.side_effect = requests.Timeout("timeout")
    with pytest.raises(WeatherAdapterError, match="temporarily unavailable"):
        OpenMeteoAdapter(session).resolve_location("Lisbon")


def test_days_out_of_range_is_rejected_without_http_call():
    session = Mock()
    with pytest.raises(WeatherAdapterError, match="between 1 and 16"):
        OpenMeteoAdapter(session).get_forecast("Lisbon", 17)
    session.get.assert_not_called()
