import importlib
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
def real_tavily_key() -> str:
    backend_dir = Path(__file__).resolve().parents[1]
    project_root = backend_dir.parent

    tavily_key = (
        os.environ.get("TAVILY_API_KEY")
        or _read_env_value(backend_dir / ".env", "TAVILY_API_KEY")
        or _read_env_value(project_root / ".env", "TAVILY_API_KEY")
    )

    if not tavily_key or tavily_key.startswith("test-"):
        pytest.skip("需要设置真实 TAVILY_API_KEY 才能运行 Tavily 真实请求测试")

    return tavily_key


@pytest.fixture(scope="module")
def web_search_tools(real_tavily_key: str) -> Any:
    os.environ["DEBUG"] = "false"
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    os.environ["TAVILY_API_KEY"] = real_tavily_key

    web_search_module = importlib.import_module("backend.core.tools.web_search")

    web_search_module.settings.tavily_api_key = real_tavily_key
    return web_search_module


@pytest.mark.integration
def test_web_search_real_request(web_search_tools: Any) -> None:
    result = web_search_tools.web_search.invoke({"query": "Tavily search API documentation"})

    assert not result.startswith("抱歉")
    assert "找到" in result
    assert "来源：" in result
    assert "http" in result


@pytest.mark.integration
def test_web_search_tool_simple_real_request(web_search_tools: Any) -> None:
    result = web_search_tools.web_search_tool_simple.invoke(
        {"query": "LangChain TavilySearch documentation"}
    )

    assert not result.startswith("搜索失败")
    assert result.startswith("快速搜索结果")
    assert "http" in result
