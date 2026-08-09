from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import Mock


SERVER_DIR = Path(__file__).parents[1] / "mcp_server"
sys.path.insert(0, str(SERVER_DIR))
server = importlib.import_module("weather_mcp_server")


def test_recommendation_applies_all_documented_thresholds(monkeypatch):
    fake = Mock()
    fake.get_forecast_for_date.return_value = {
        "location": "Austin, Texas, United States",
        "date": "2026-08-10",
        "temperature_min_c": 10,
        "temperature_max_c": 28,
        "precipitation_probability_percent": 40,
        "precipitation_sum_mm": 2,
        "wind_speed_max_kmh": 40,
        "uv_index_max": 7,
        "weather_code": 61,
        "conditions": "slight rain",
    }
    monkeypatch.setattr(server, "weather", fake)
    result = server.get_weather_recommendation.fn("Austin", "2026-08-10")
    assert result["ok"] is True
    assert len(result["data"]["recommendations"]) == 4
    assert "precipitation_probability_percent >= 40" in result["data"]["triggered_rules"]


def test_tool_returns_clean_adapter_error(monkeypatch):
    fake = Mock()
    fake.get_current_weather.side_effect = server.WeatherAdapterError("Location was not found.")
    monkeypatch.setattr(server, "weather", fake)
    result = server.get_current_weather.fn("X")
    assert result == {"ok": False, "error": "Location was not found."}
