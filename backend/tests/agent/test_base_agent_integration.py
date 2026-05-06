import asyncio
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


def _backend_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if parent.name == "backend" and (parent / "pyproject.toml").exists():
            return parent

    raise RuntimeError("无法定位 backend 项目目录")


def _read_config_value(backend_dir: Path, key: str) -> str:
    project_root = backend_dir.parent
    return (
        os.environ.get(key)
        or _read_env_value(backend_dir / ".env", key)
        or _read_env_value(project_root / ".env", key)
    )


@pytest.fixture(scope="module")
def real_openai_config() -> dict[str, str]:
    backend_dir = _backend_dir()

    api_key = _read_config_value(backend_dir, "OPENAI_API_KEY")
    model = _read_config_value(backend_dir, "MODEL_NAME") or _read_config_value(
        backend_dir, "OPENAI_MODEL"
    )
    base_url = _read_config_value(backend_dir, "OPENAI_BASE_URL")

    if not api_key or api_key.startswith("test-"):
        pytest.skip("需要设置真实 OPENAI_API_KEY 才能运行 BaseAgent 真实 API 测试")

    if not model or model.startswith("test-"):
        pytest.skip("需要设置真实 MODEL_NAME 或 OPENAI_MODEL 才能运行 BaseAgent 真实 API 测试")

    os.environ["DEBUG"] = "false"
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["MODEL_NAME"] = model
    os.environ["OPENAI_MODEL"] = model
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
        os.environ["OPENAI_API_BASE"] = base_url

    return {"api_key": api_key, "model": model, "base_url": base_url}


@pytest.fixture(scope="module")
def real_base_agent(real_openai_config: dict[str, str]) -> Any:
    base_agent_module = importlib.import_module("backend.agent.base_agent")
    base_agent_module.settings.model_name = real_openai_config["model"]
    base_agent_module.settings.openai_api_key = real_openai_config["api_key"]
    if real_openai_config["base_url"]:
        base_agent_module.settings.openai_base_url = real_openai_config["base_url"]

    return base_agent_module.BaseAgent(
        model=f"openai:{real_openai_config['model']}",
        tools=[],
        system_prompt="你是一个用于集成测试的助手。回答必须简短。",
    )


def _print_answer(label: str, answer: str) -> None:
    print(f"\n{label}: {answer}", flush=True)


@pytest.mark.integration
def test_base_agent_real_api_all_call_styles_output_answers(real_base_agent: Any) -> None:
    sync_answer = real_base_agent.invoke("请只回答：同步非流式真实 API 调用成功。")
    _print_answer("AI invoke answer", sync_answer)
    assert sync_answer.strip()
    assert not sync_answer.startswith("抱歉")

    async_answer = asyncio.run(
        real_base_agent.ainvoke("请只回答：异步非流式真实 API 调用成功。")
    )
    _print_answer("AI ainvoke answer", async_answer)
    assert async_answer.strip()
    assert not async_answer.startswith("抱歉")

    for version in ("v1", "v2"):
        print(f"\nAI stream {version} answer: ", end="", flush=True)
        stream_chunks = list(
            real_base_agent.stream(
                f"请只回答：同步流式 {version} 真实 API 调用成功。",
                stream_mode="messages",
                version=version,
            )
        )
        stream_answer = "".join(stream_chunks)
        print(stream_answer, flush=True)
        assert stream_answer.strip()
        assert not stream_answer.startswith("抱歉")

    async def collect_astream(version: str) -> str:
        print(f"\nAI astream {version} answer: ", end="", flush=True)
        chunks = [
            chunk
            async for chunk in real_base_agent.astream(
                f"请只回答：异步流式 {version} 真实 API 调用成功。",
                stream_mode="messages",
                version=version,
            )
        ]
        answer = "".join(chunks)
        print(answer, flush=True)
        return answer

    for version in ("v1", "v2"):
        astream_answer = asyncio.run(collect_astream(version))
        assert astream_answer.strip()
        assert not astream_answer.startswith("抱歉")
