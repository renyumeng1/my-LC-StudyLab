from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


WeatherStatus = Literal["0", "1"]
WeatherExtensions = Literal["base", "all"]
WeatherOutput = Literal["JSON", "XML"]


class AmapWeatherRequestParams(BaseModel):
    """高德天气接口请求参数。"""

    key: str = Field(description="高德地图 Web 服务 API Key")
    city: str = Field(description="城市 adcode")
    extensions: WeatherExtensions = Field(
        default="base",
        description="气象类型，base 返回实况天气，all 返回预报天气",
    )
    output: WeatherOutput = Field(default="JSON", description="返回格式")


class AmapLiveWeather(BaseModel):
    """高德实况天气数据。"""

    model_config = ConfigDict(extra="ignore")

    province: str | None = Field(default=None, description="省份名")
    city: str | None = Field(default=None, description="城市名")
    adcode: str | None = Field(default=None, description="区域编码")
    weather: str | None = Field(default=None, description="天气现象")
    temperature: str | None = Field(default=None, description="实时气温，单位：摄氏度")
    winddirection: str | None = Field(default=None, description="风向描述")
    windpower: str | None = Field(default=None, description="风力级别")
    humidity: str | None = Field(default=None, description="空气湿度")
    reporttime: str | None = Field(default=None, description="数据发布时间")
    temperature_float: str | None = Field(default=None, description="实时气温浮点值")
    humidity_float: str | None = Field(default=None, description="空气湿度浮点值")


class AmapForecastCast(BaseModel):
    """高德单日预报天气数据。"""

    model_config = ConfigDict(extra="ignore")

    date: str | None = Field(default=None, description="日期")
    week: str | None = Field(default=None, description="星期几")
    dayweather: str | None = Field(default=None, description="白天天气现象")
    nightweather: str | None = Field(default=None, description="晚上天气现象")
    daytemp: str | None = Field(default=None, description="白天温度")
    nighttemp: str | None = Field(default=None, description="晚上温度")
    daywind: str | None = Field(default=None, description="白天风向")
    nightwind: str | None = Field(default=None, description="晚上风向")
    daypower: str | None = Field(default=None, description="白天风力")
    nightpower: str | None = Field(default=None, description="晚上风力")


class AmapForecastWeather(BaseModel):
    """高德预报天气数据。"""

    model_config = ConfigDict(extra="ignore")

    city: str | None = Field(default=None, description="城市名称")
    adcode: str | None = Field(default=None, description="城市编码")
    province: str | None = Field(default=None, description="省份名称")
    reporttime: str | None = Field(default=None, description="预报发布时间")
    casts: list[AmapForecastCast] = Field(
        default_factory=list,
        description="预报数据，按顺序为当天、第二天、第三天等",
    )


class AmapWeatherResponse(BaseModel):
    """高德天气接口响应数据。

    extensions="base" 时返回 lives；extensions="all" 时返回 forecasts。
    """

    model_config = ConfigDict(extra="ignore")

    status: WeatherStatus = Field(description="返回状态，1 表示成功，0 表示失败")
    count: str = Field(description="返回结果总数目")
    info: str = Field(default="",description="返回的状态信息")
    infocode: str = Field(description="返回状态说明，10000 代表正确")
    lives: list[AmapLiveWeather] = Field(default_factory=list, description="实况天气数据")
    forecasts: list[AmapForecastWeather] = Field(default_factory=list, description="预报天气数据")
