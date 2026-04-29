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


def _get_weather_impl(
    city: str,
    extensions: Literal["base", "all"] = "base",
    day_offset: Optional[int] = None,
) -> str:
    """天气查询函数底层实现函数

    Args:
        city (str): 城市名称或城市编码
        extensions (Literal["base","all"], optional): 气象类型（"base"或"all"）. Defaults to "base".
        day_offset (Optional[int], optional): 预报日期偏移，0 表示今天，1 表示明天，2 表示后天。Defaults to None.

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
        key=amap_key, city=city, extensions=extensions, output="JSON"
    )

    logger.info(
        f"🌤️ 查询天气: city={city}, extensions={extensions}, day_offset={day_offset}"
    )

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params.model_dump())
            response.raise_for_status()

            weather_response: AmapWeatherResponse = AmapWeatherResponse.model_validate(
                response.json()
            )

            if weather_response.status != "1":
                error_msg = f"天气查询失败：{weather_response.info or '未知错误'}"
                logger.error(error_msg)
                return f"错误：{error_msg}"

            if extensions == "base":
                # 实况天气
                return _format_live_weather(weather_response)

            else:
                # 预报天气
                return _format_forecast_weather(
                    weather_response, day_offset=day_offset
                )

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


@tool
def get_weather(
    city:str,
    extensions:Literal["base", "all"] = "base",
)->str:
    """
    查询指定城市的天气信息
    
    支持查询实况天气和预报天气：
    - base: 返回实况天气（当前天气状况）
    - all: 返回预报天气（未来3天预报）
    
    Args:
        city: 城市名称或城市编码（adcode）
              例如："北京"、"110101"
              城市编码表可参考：https://lbs.amap.com/api/webservice/download
        extensions: 气象类型
                   "base" - 返回实况天气（默认）
                   "all" - 返回预报天气
    
    Returns:
        格式化的天气信息字符串
        
    Example:
        >>> # 查询北京实况天气
        >>> result = get_weather.invoke({"city": "北京"})
        >>> print(result)
        
        >>> # 查询上海未来天气预报
        >>> result = get_weather.invoke({"city": "上海", "extensions": "all"})
        >>> print(result)
    
    注意：
        - 实况天气每小时更新多次
        - 预报天气每天更新3次（8点、11点、18点左右）
        - 需要在 .env 文件中设置 AMAP_KEY
    """
    return _get_weather_impl(city=city, extensions=extensions)

@tool
def get_weather_forecast(city:str)->str:
    """
    查询指定城市未来3天的天气预报
    
    这是 get_weather 的便捷版本，直接返回预报天气。
    
    Args:
        city: 城市名称或城市编码（adcode）
              例如："北京"、"上海"、"广州"
    
    Returns:
        格式化的天气预报信息字符串
        
    Example:
        >>> result = get_weather_forecast.invoke({"city": "深圳"})
        >>> print(result)
    """
    
    return _get_weather_impl(city=city, extensions="all")


@tool
def get_daily_weather(
    city: str,
    day: Literal["today", "tomorrow", "day_after_tomorrow"] = "tomorrow",
) -> str:
    """查询指定城市某一天的天气预报。

    这个工具内部会直接查询预报天气接口，不需要先调用 get_current_date 或
    get_current_time。

    当用户问“今天天气”“明天天气”“后天天气”时，优先使用这个工具，并显式传入
    day 参数。

    Args:
        city: 城市名称或城市编码（adcode），例如："北京"、"上海"、"深圳"、"广州"。
        day: 查询哪一天的天气。
            - "today": 今天
            - "tomorrow": 明天，默认值
            - "day_after_tomorrow": 后天

    Returns:
        只包含指定日期的格式化天气预报信息字符串。

    Example:
        >>> get_daily_weather.invoke({"city": "深圳", "day": "today"})
        >>> get_daily_weather.invoke({"city": "北京", "day": "tomorrow"})
        >>> get_daily_weather.invoke({"city": "上海", "day": "day_after_tomorrow"})

    注意：
        - 不要先调用 get_current_date 或 get_current_time。
        - 查询今天时传 day="today"。
        - 查询明天时传 day="tomorrow"。
        - 查询后天时传 day="day_after_tomorrow"。
        - 该工具只返回指定那一天，适合用户只问某一天天气的场景。
    """
    day_offset_map = {
        "today": 0,
        "tomorrow": 1,
        "day_after_tomorrow": 2,
    }
    day_offset = day_offset_map[day]

    logger.info(f"🌤️ 查询单日天气: city={city}, day={day}, day_offset={day_offset}")
    return _get_weather_impl(city=city, extensions="all", day_offset=day_offset)



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


def _get_day_name(day_offset: int) -> str:
    """根据预报日期偏移返回自然语言日期描述。"""
    day_names = ["今天", "明天", "后天"]
    if day_offset < len(day_names):
        return day_names[day_offset]

    return f"{day_offset}天后"


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

    result = "\n".join(
        [
            f"地区：{_display_text(live.province)} {_display_text(live.city)}",
            f"天气：{_display_text(live.weather)}",
            f"温度：{_with_unit(live.temperature, '°C')}",
            f"风向：{_display_text(live.winddirection)}",
            f"风力：{_with_unit(live.windpower, '级')}",
            f"湿度：{_with_unit(live.humidity, '%')}",
            f"数据发布时间：{_display_text(live.reporttime)}",
        ]
    )

    logger.info(f"实况天气查询成功：{live.city}")

    return result


def _format_forecast_weather(
    weather_response: AmapWeatherResponse, day_offset: Optional[int] = None
) -> str:
    """格式化预报天气信息为字符串

    Args:
        weather_response (AmapWeatherResponse): 高德天气接口响应数据

    Returns:
        str: 格式化的预报天气信息字符串
    """
    if not weather_response.forecasts:
        return "未获取到预报天气数据。"

    forecast = weather_response.forecasts[0]

    if not forecast.casts:
        return "未获取到逐日预报数据。"

    province = _display_text(forecast.province, default="")
    city = _display_text(forecast.city, default="")
    area = " ".join(part for part in [province, city] if part) or "未知"
    reporttime = _display_text(forecast.reporttime)
    casts = forecast.casts

    if day_offset is not None:
        if day_offset < 0 or day_offset >= len(casts):
            return f"错误：无法查询第 {day_offset} 天的天气（可用范围: 0-{len(casts) - 1}）"

        cast = casts[day_offset]
        day_name = _get_day_name(day_offset)
        result = (
            f"📍 地区：{area}\n"
            f"⏰ 预报发布时间：{reporttime}\n\n"
            f"📅 {day_name}（{_display_text(cast.date)} {_format_week(cast.week)}）\n"
            f"  🌞 白天：{_display_text(cast.dayweather)}  "
            f"{_with_unit(cast.daytemp, '°C')}  "
            f"{_display_text(cast.daywind)}风{_with_unit(cast.daypower, '级')}\n"
            f"  🌙 夜间：{_display_text(cast.nightweather)}  "
            f"{_with_unit(cast.nighttemp, '°C')}  "
            f"{_display_text(cast.nightwind)}风{_with_unit(cast.nightpower, '级')}"
        )
        logger.info(f"✅ 预报天气查询成功: {city or area} {day_name}")
        return result

    lines = [
        f"📍 地区：{area}",
        f"⏰ 预报发布时间：{reporttime}",
        "",
    ]

    for idx, cast in enumerate(casts):
        day_name = _get_day_name(idx)
        lines.append(
            "\n".join(
                [
                    f"📅 {day_name}（{_display_text(cast.date)} {_format_week(cast.week)}）",
                    (
                        f"  🌞 白天：{_display_text(cast.dayweather)}  "
                        f"{_with_unit(cast.daytemp, '°C')}  "
                        f"{_display_text(cast.daywind)}风{_with_unit(cast.daypower, '级')}"
                    ),
                    (
                        f"  🌙 夜间：{_display_text(cast.nightweather)}  "
                        f"{_with_unit(cast.nighttemp, '°C')}  "
                        f"{_display_text(cast.nightwind)}风{_with_unit(cast.nightpower, '级')}"
                    ),
                ]
            )
        )

    logger.info(f"✅ 预报天气查询成功: {city or area} ({len(casts)}天)")
    return "\n".join(lines)


# 导出工具
__all__ = [
    "get_weather",
    "get_weather_forecast",
    "get_daily_weather",
]
