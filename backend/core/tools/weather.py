import httpx
from pydantic import ValidationError

from datetime import datetime, timedelta
from typing import Optional, Literal
from langchain.tools import tool

from backend.schemas.weather import AmapWeatherResponse

from ...config import settings, get_logger

from ...schemas import (
    AmapWeatherRequestParams,
    AmapLiveWeather,
    AmapForecastCast,
    AmapForecastWeather,
)


logger = get_logger(__name__)


def _get_weather_impl(city: str, extensions: Literal["base", "all"] = "base") -> str:
    """天气查询函数底层实现函数

    Args:
        city (str): 城市名称或城市编码
        extensions (Literal[&quot;base&quot;,&quot;all&quot;], optional): 气象类型（"base"或"all"）. Defaults to "base".

    Returns:
        str: 格式化的天气信息字符串
    """
    amap_key = getattr(settings, "amap_key", None)

    if not amap_key:
        error_msg = "高德地图 API Key 未设置！请在 .env 文件中设置 AMAP_KEY。\n获取 API Key: https://console.amap.com/"
        logger.error(error_msg)
        return f"错误：{error_msg}"

    # API 端点
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    
    params: AmapWeatherRequestParams = AmapWeatherRequestParams(
        key=amap_key,
        city=city,
        extensions=extensions,
        output="JSON"
    )
    
    logger.info(f"🌤️ 查询天气: city={city}, extensions={extensions}")
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params.model_dump())
            response.raise_for_status()
            
            weather_response:AmapWeatherResponse = AmapWeatherResponse.model_validate(response.json())
            
            if weather_response.status != "1":
                error_msg = f"天气查询失败：{weather_response.info or '未知错误'}"
                logger.error(error_msg)
                return f"错误：{error_msg}"
            
            if extensions == "base":
                # 实况天气
                return _format_live_weather(weather_response)
            
            else:
                # 预报天气
                return _format_forecast_weather(weather_response)
    
    except ValidationError:
        error_msg = "天气数据解析失败，可能是接口返回格式发生了变化。"
        logger.error(error_msg, exc_info=True)
        return f"错误：{error_msg}"
    except httpx.TimeoutException:
        error_msg = "天气查询超时，请稍后重试"
        logger.error(error_msg)
        return f"错误：{error_msg}"
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP 请求失败: {e.response.status_code}"
        logger.error(error_msg)
        return f"错误：{error_msg}"
    except Exception as e:
        error_msg = f"天气查询出错: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"错误：{error_msg}"


def _display_text(value: str | None, default: str = "未知") -> str:
    """返回适合展示的文本，避免输出 None 或空字符串。"""
    if value is None:
        return default

    text = str(value).strip()
    return text or default


def _with_unit(value: str | None, unit: str) -> str:
    """给非空数值追加单位；缺失时返回未知。"""
    text = _display_text(value, default="")
    if not text:
        return "未知"

    return f"{text}{unit}"


def _format_week(week: str | None) -> str:
    """格式化高德返回的星期值。"""
    week_text = _display_text(week, default="")
    if not week_text:
        return "未知"

    week_map = {
        "1": "星期一",
        "2": "星期二",
        "3": "星期三",
        "4": "星期四",
        "5": "星期五",
        "6": "星期六",
        "7": "星期日",
    }
    return week_map.get(week_text, week_text)

def _format_live_weather(weather_response: AmapWeatherResponse) -> str:
    """格式化实况天气信息为字符串

    Args:
        weather_response (AmapWeatherResponse): 高德天气接口响应数据

    Returns:
        str: 格式化的实况天气信息字符串
    """
    if not weather_response.lives:
        return "未获取到实况天气数据。"
    
    live = weather_response.lives[0]
    
    return "\n".join(
        [
            f"城市：{_display_text(live.city)}",
            f"天气：{_display_text(live.weather)}",
            f"温度：{_with_unit(live.temperature, '°C')}",
            f"风向：{_display_text(live.winddirection)}",
            f"风力：{_with_unit(live.windpower, '级')}",
            f"湿度：{_with_unit(live.humidity, '%')}",
            f"数据发布时间：{_display_text(live.reporttime)}",
        ]
    )


def _format_forecast_weather(weather_response: AmapWeatherResponse) -> str:
    """格式化预报天气信息为字符串

    Args:
        weather_response (AmapWeatherResponse): 高德天气接口响应数据

    Returns:
        str: 格式化的预报天气信息字符串
    """
    if not weather_response.forecasts:
        return "未获取到预报天气数据。"
    
    forecast = weather_response.forecasts[0]
    
    lines = [
        f"城市：{_display_text(forecast.city)}",
        f"预报发布时间：{_display_text(forecast.reporttime)}",
    ]

    if not forecast.casts:
        lines.append("未获取到逐日预报数据。")
        return "\n".join(lines)

    for cast in forecast.casts:
        lines.extend(
            [
                "",
                f"日期：{_display_text(cast.date)} （{_format_week(cast.week)}）",
                (
                    f"白天天气：{_display_text(cast.dayweather)}，"
                    f"温度：{_with_unit(cast.daytemp, '°C')}，"
                    f"风向：{_display_text(cast.daywind)}，"
                    f"风力：{_with_unit(cast.daypower, '级')}"
                ),
                (
                    f"晚上天气：{_display_text(cast.nightweather)}，"
                    f"温度：{_with_unit(cast.nighttemp, '°C')}，"
                    f"风向：{_display_text(cast.nightwind)}，"
                    f"风力：{_with_unit(cast.nightpower, '级')}"
                ),
            ]
        )
    
    return "\n".join(lines)
