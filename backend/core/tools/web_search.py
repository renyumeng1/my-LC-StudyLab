from typing import Literal, Optional

from langchain.tools import tool

from ...config import settings, get_logger
from ...schemas import TavilySearchParams, TavilySearchResponse

logger = get_logger(__name__)

from langchain_tavily import TavilySearch


def create_tavily_search_tool(
    max_results: Optional[int] = None,
    search_depth: Literal["advanced", "basic", "fast", "ultra-fast"] = "advanced",
    include_domains: Optional[list[str]] = None,
    exclude_domains: Optional[list[str]] = None,
) -> TavilySearch:
    """创建 Tavily 搜索工具。

    Args:
        max_results: 最大返回结果数量。为 ``None`` 时使用配置项
            ``settings.tavily_max_results``。
        search_depth: 搜索深度，可选值为 ``"basic"``、``"advanced"``、
            ``"fast"`` 或 ``"ultra-fast"``。默认为 ``"advanced"``。
        include_domains: 仅搜索指定域名列表；为 ``None`` 时不限制包含域名。
        exclude_domains: 排除指定域名列表；为 ``None`` 时不设置排除域名。

    Returns:
        配置完成的 ``TavilySearch`` 工具实例，可直接交给 LangChain Agent 调用。

    Raises:
        Exception: TavilySearch 初始化失败时记录错误并重新抛出原异常。
    """

    max_results = max_results or settings.tavily_max_results

    logger.info(
        f"🔍 创建 Tavily 搜索工具 (max_results={max_results}, depth={search_depth})"
    )

    tool_kwargs: TavilySearchParams = TavilySearchParams(
        max_results=max_results,
        search_depth=search_depth,
        tavily_api_key=settings.tavily_api_key,
    )

    if include_domains is not None:
        tool_kwargs["include_domains"] = include_domains
    if exclude_domains is not None:
        tool_kwargs["exclude_domains"] = exclude_domains

    try:
        tool = TavilySearch(**tool_kwargs)
        return tool
    except Exception as e:
        logger.error(f"创建 Tavily 搜索工具失败: {e}")
        raise



def _invoke_tavily_search(
    query: str,
    *,
    max_results: Optional[int] = None,
    search_depth: Literal["advanced", "basic", "fast", "ultra-fast"] = "advanced",
) -> TavilySearchResponse:
    search_tool = create_tavily_search_tool(
        max_results=max_results,
        search_depth=search_depth,
    )
    raw_results = search_tool.invoke({"query": query})
    return TavilySearchResponse.model_validate(raw_results)


def _format_tavily_search_results(
    query: str,
    search_response: TavilySearchResponse,
    *,
    heading: str,
    include_answer: bool = False,
    include_content: bool = True,
) -> str:
    results = search_response.results

    if not results:
        logger.info("📭 未找到搜索结果")
        return f"未找到关于 '{query}' 的相关信息。"

    formatted_results = [heading.format(count=len(results))]

    if include_answer and search_response.answer:
        formatted_results.append(f"\n回答：{search_response.answer}")

    for index, result in enumerate(results, 1):
        title = result.title or "无标题"
        url = result.url or ""

        if not include_content:
            formatted_results.append(f"{index}. {title} - {url}")
            continue

        content = result.content or ""
        if len(content) > 2000:
            content = content[:2000] + "..."

        formatted_results.append(f"\n{index}. {title}")

        if content:
            formatted_results.append(f"   内容：{content}")
        if url:
            formatted_results.append(f"   来源：{url}")

    return "\n".join(formatted_results)

@tool
def web_search(query: str) -> str:
    """使用 Tavily 执行网络搜索并返回摘要文本。"""

    logger.info(f"执行 Web 搜索工具，查询: {query}")

    try:
        if not settings.tavily_api_key:
            logger.warning("Tavily API Key 未配置，无法执行 Web 搜索")
            return (
                "抱歉，网络搜索功能暂时不可用（未配置 Tavily API Key）。"
                "请在 .env 文件中设置 TAVILY_API_KEY。"
            )

        search_response = _invoke_tavily_search(query)
        result_text = _format_tavily_search_results(
            query,
            search_response,
            heading="找到 {count} 条结果：",
            include_answer=True,
            include_content=True,
        )
        logger.info(f"✅ 搜索完成，找到 {len(search_response.results)} 条结果")
        return result_text
    except Exception as e:
        error_msg = f"执行 Web 搜索工具时发生错误: {str(e)}"
        logger.error(error_msg)
        return f"抱歉，执行网络搜索时发生错误：{str(e)}"
            

@tool
def web_search_tool_simple(query: str) -> str:
    """使用 Tavily 执行快速网络搜索，只返回标题和来源链接。"""

    logger.info(f"🔍 执行快速搜索: {query}")

    try:
        if not settings.tavily_api_key:
            return "网络搜索功能暂时不可用（未配置 API Key）"

        search_response = _invoke_tavily_search(
            query,
            max_results=3,
            search_depth="basic",
        )
        result_text = _format_tavily_search_results(
            query,
            search_response,
            heading="快速搜索结果（{count} 条）：",
            include_content=False,
        )
        logger.info(f"✅ 快速搜索完成，找到 {len(search_response.results)} 条结果")
        return result_text
    except Exception as e:
        logger.error(f"❌ 快速搜索失败: {e}")
        return f"搜索失败: {str(e)}"


__all__ = [
    "web_search",
    "web_search_tool_simple",
    "create_tavily_search_tool",
]

if __name__ == "__main__":
    # 简单测试
    result = web_search.invoke({"query": "deepseek最新模型是什么？"})
    print(result)

