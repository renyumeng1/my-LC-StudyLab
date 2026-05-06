import os
from pathlib import Path
from typing import Any

import pytest


def _read_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        if name.strip().upper() == key.upper():
            return value.strip().strip("\"'")

    return ""


@pytest.fixture(scope="module")
def real_amap_key() -> str:
    backend_dir = Path(__file__).resolve().parents[1]
    project_root = backend_dir.parent

    amap_key = (
        os.environ.get("AMAP_KEY")
        or _read_env_value(backend_dir / ".env", "AMAP_KEY")
        or _read_env_value(project_root / ".env", "AMAP_KEY")
    )

    if not amap_key or amap_key.startswith("test-"):
        pytest.skip("需要设置真实 AMAP_KEY 才能运行高德天气真实请求测试")

    return amap_key


@pytest.fixture(scope="module")
def weather_tools(real_amap_key: str) -> Any:
    os.environ["DEBUG"] = "false"
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    os.environ["AMAP_KEY"] = real_amap_key

    import backend.core.tools.weather as weather_module

    weather_module.settings.amap_key = real_amap_key
    return weather_module


@pytest.mark.integration
def test_get_weather_real_request(weather_tools: Any) -> None:
    result = weather_tools.get_weather.invoke({"city": "110101"})

    assert not result.startswith("错误：")
    assert "地区：" in result
    assert "天气：" in result
    assert "温度：" in result


@pytest.mark.integration
def test_get_weather_forecast_real_request(weather_tools: Any) -> None:
    result = weather_tools.get_weather_forecast.invoke({"city": "110101"})

    assert not result.startswith("错误：")
    assert "📍 地区：" in result
    assert "⏰ 预报发布时间：" in result
    assert "📅 今天" in result


@pytest.mark.integration
def test_get_daily_weather_real_request(weather_tools: Any) -> None:
    result = weather_tools.get_daily_weather.invoke(
        {"city": "110101", "day": "tomorrow"}
    )

    assert not result.startswith("错误：")
    assert "📍 地区：" in result
    assert "📅 明天" in result
    assert "🌞 白天：" in result
    assert "🌙 夜间：" in result
