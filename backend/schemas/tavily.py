from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field


TavilySearchDepth = Literal["advanced", "basic", "fast", "ultra-fast"]
TavilyTopic = Literal["general", "news", "finance"]


class TavilySearchParams(TypedDict):
    max_results: int
    search_depth: TavilySearchDepth
    tavily_api_key: str
    include_domains: NotRequired[list[str]]
    exclude_domains: NotRequired[list[str]]


class TavilySearchImage(BaseModel):
    """Tavily 搜索返回的图片信息。"""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(description="图片 URL")
    description: str | None = Field(default=None, description="图片描述")


class TavilySearchResultItem(BaseModel):
    """Tavily 搜索结果列表中的单条网页结果。"""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(default="", description="网页标题")
    url: str = Field(default="", description="网页 URL")
    content: str = Field(default="", description="搜索结果摘要或相关片段")
    score: float | None = Field(default=None, description="结果相关性评分")
    raw_content: str | None = Field(default=None, description="原始网页正文内容")
    favicon: str | None = Field(default=None, description="网站 favicon URL")
    images: list[TavilySearchImage | str] = Field(
        default_factory=list,
        description="该结果来源页面提取到的图片",
    )


class TavilyAutoParameters(BaseModel):
    """auto_parameters 开启时 Tavily 自动选择的参数。"""

    model_config = ConfigDict(extra="ignore")

    topic: TavilyTopic | None = Field(default=None, description="自动选择的搜索主题")
    search_depth: TavilySearchDepth | None = Field(
        default=None,
        description="自动选择的搜索深度",
    )


class TavilyUsage(BaseModel):
    """Tavily 请求用量信息。"""

    model_config = ConfigDict(extra="ignore")

    credits: int | float | None = Field(default=None, description="本次请求消耗的额度")


class TavilySearchResponse(BaseModel):
    """``TavilySearch.invoke`` 成功时返回的搜索响应。"""

    model_config = ConfigDict(extra="ignore")

    query: str = Field(description="实际执行的搜索查询")
    answer: str | None = Field(default=None, description="LLM 生成的简短回答")
    follow_up_questions: list[str] | None = Field(
        default=None,
        description="后续追问建议，部分版本可能返回该字段",
    )
    images: list[TavilySearchImage | str] = Field(
        default_factory=list,
        description="和查询相关的图片列表",
    )
    results: list[TavilySearchResultItem] = Field(
        default_factory=list,
        description="按相关性排序的搜索结果",
    )
    response_time: float | str | None = Field(
        default=None,
        description="请求耗时，单位为秒；不同版本可能返回数字或字符串",
    )
    auto_parameters: TavilyAutoParameters | None = Field(
        default=None,
        description="auto_parameters 开启时返回的自动参数",
    )
    usage: TavilyUsage | None = Field(default=None, description="请求用量信息")
    request_id: str | None = Field(default=None, description="Tavily 请求 ID")


class TavilySearchErrorResponse(BaseModel):
    """``TavilySearch.invoke`` 捕获底层异常时可能返回的错误响应。"""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    error: Any = Field(description="底层 Tavily 调用返回的错误对象或错误信息")
