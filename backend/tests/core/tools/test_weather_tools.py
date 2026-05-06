import importlib
from typing import Any

import pytest


@pytest.fixture
def weather_modules(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("AMAP_KEY", "test-amap-key")

    tools_package = importlib.import_module("backend.core.tools")
    weather_module = importlib.import_module("backend.core.tools.weather")
    return tools_package, weather_module


def test_get_weather_routes_to_weather_impl(
    weather_modules: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools_package, weather_module = weather_modules
    calls: list[dict[str, Any]] = []

    def fake_get_weather_impl(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "live weather"

    monkeypatch.setattr(weather_module, "_get_weather_impl", fake_get_weather_impl)

    assert tools_package.get_weather.invoke({"city": "北京"}) == "live weather"
    assert calls == [{"city": "北京", "extensions": "base"}]

    assert (
        tools_package.get_weather.invoke({"city": "上海", "extensions": "all"})
        == "live weather"
    )
    assert calls[-1] == {"city": "上海", "extensions": "all"}


def test_get_weather_forecast_routes_to_forecast_impl(
    weather_modules: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools_package, weather_module = weather_modules
    calls: list[dict[str, Any]] = []

    def fake_get_weather_impl(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "forecast weather"

    monkeypatch.setattr(weather_module, "_get_weather_impl", fake_get_weather_impl)

    assert tools_package.get_weather_forecast.invoke({"city": "深圳"}) == "forecast weather"
    assert calls == [{"city": "深圳", "extensions": "all"}]


@pytest.mark.parametrize(
    ("day", "expected_offset"),
    [
        ("today", 0),
        ("tomorrow", 1),
        ("day_after_tomorrow", 2),
    ],
)
def test_get_daily_weather_maps_day_to_day_offset(
    weather_modules: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
    day: str,
    expected_offset: int,
) -> None:
    tools_package, weather_module = weather_modules
    calls: list[dict[str, Any]] = []

    def fake_get_weather_impl(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "daily weather"

    monkeypatch.setattr(weather_module, "_get_weather_impl", fake_get_weather_impl)

    result = tools_package.get_daily_weather.invoke({"city": "广州", "day": day})

    assert result == "daily weather"
    assert calls == [
        {
            "city": "广州",
            "extensions": "all",
            "day_offset": expected_offset,
        }
    ]


def test_get_daily_weather_defaults_to_tomorrow(
    weather_modules: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools_package, weather_module = weather_modules
    calls: list[dict[str, Any]] = []

    def fake_get_weather_impl(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "daily weather"

    monkeypatch.setattr(weather_module, "_get_weather_impl", fake_get_weather_impl)

    assert tools_package.get_daily_weather.invoke({"city": "广州"}) == "daily weather"
    assert calls == [{"city": "广州", "extensions": "all", "day_offset": 1}]
