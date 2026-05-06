import asyncio
import importlib
from typing import Any

import pytest


@pytest.fixture
def base_agent_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    return importlib.import_module("backend.agent.base_agent")


class _TokenWithContentBlocks:
    def __init__(self, text: str) -> None:
        self.content_blocks = [{"type": "text", "text": text}]


class _FakeGraph:
    def __init__(
        self,
        *,
        invoke_result: dict[str, Any] | None = None,
        ainvoke_result: dict[str, Any] | None = None,
        stream_chunks: list[Any] | None = None,
        astream_chunks: list[Any] | None = None,
    ) -> None:
        self.invoke_result = invoke_result or {}
        self.ainvoke_result = ainvoke_result or {}
        self.stream_chunks = stream_chunks or []
        self.astream_chunks = astream_chunks or []
        self.invoke_input: dict[str, Any] | None = None
        self.ainvoke_input: dict[str, Any] | None = None
        self.ainvoke_config: Any = None
        self.stream_call: dict[str, Any] | None = None
        self.astream_call: dict[str, Any] | None = None

    def invoke(self, graph_input: dict[str, Any]) -> dict[str, Any]:
        self.invoke_input = graph_input
        return self.invoke_result

    async def ainvoke(
        self, graph_input: dict[str, Any], config: Any = None
    ) -> dict[str, Any]:
        self.ainvoke_input = graph_input
        self.ainvoke_config = config
        return self.ainvoke_result

    def stream(
        self, *, input: dict[str, Any], stream_mode: str, version: str
    ) -> Any:
        self.stream_call = {
            "input": input,
            "stream_mode": stream_mode,
            "version": version,
        }
        yield from self.stream_chunks

    async def astream(
        self, graph_input: dict[str, Any], stream_mode: str, version: str
    ) -> Any:
        self.astream_call = {
            "input": graph_input,
            "stream_mode": stream_mode,
            "version": version,
        }
        for chunk in self.astream_chunks:
            yield chunk


def _agent_with_graph(base_agent_module: Any, graph: _FakeGraph) -> Any:
    agent = object.__new__(base_agent_module.BaseAgent)
    agent.graph = graph
    return agent


def test_invoke_returns_last_ai_message_and_passes_input(base_agent_module: Any) -> None:
    graph = _FakeGraph(
        invoke_result={
            "messages": [
                base_agent_module.AIMessage(content="first"),
                base_agent_module.AIMessage(content="sync final"),
            ]
        }
    )
    agent = _agent_with_graph(base_agent_module, graph)
    history = [base_agent_module.HumanMessage(content="history")]

    result = agent.invoke("current", chat_history=history, trace_id="sync")

    assert result == "sync final"
    assert graph.invoke_input is not None
    assert graph.invoke_input["trace_id"] == "sync"
    assert [message.content for message in graph.invoke_input["messages"]] == [
        "history",
        "current",
    ]


def test_ainvoke_returns_last_ai_message_and_passes_config(
    base_agent_module: Any,
) -> None:
    graph = _FakeGraph(
        ainvoke_result={
            "messages": [
                base_agent_module.AIMessage(content="first"),
                base_agent_module.AIMessage(content="async final"),
            ]
        }
    )
    agent = _agent_with_graph(base_agent_module, graph)
    config = {"configurable": {"thread_id": "thread-1"}}

    result = asyncio.run(agent.ainvoke("current", config=config, trace_id="async"))

    assert result == "async final"
    assert graph.ainvoke_input is not None
    assert graph.ainvoke_input["trace_id"] == "async"
    assert graph.ainvoke_input["messages"][-1].content == "current"
    assert graph.ainvoke_config is config


@pytest.mark.parametrize(
    ("stream_mode", "version", "chunk_factory", "expected"),
    [
        (
            "messages",
            "v1",
            lambda module: [(module.AIMessage(content="sync messages v1"), {})],
            ["sync messages v1"],
        ),
        (
            "messages",
            "v2",
            lambda module: [
                {
                    "type": "messages",
                    "ns": (),
                    "data": (_TokenWithContentBlocks("sync messages v2"), {}),
                }
            ],
            ["sync messages v2"],
        ),
        (
            "updates",
            "v1",
            lambda module: [
                {"agent": {"messages": [module.AIMessage(content="sync updates v1")]}}
            ],
            ["sync updates v1"],
        ),
        (
            "updates",
            "v2",
            lambda module: [
                {
                    "type": "updates",
                    "ns": (),
                    "data": {
                        "agent": {
                            "messages": [module.AIMessage(content="sync updates v2")]
                        }
                    },
                }
            ],
            ["sync updates v2"],
        ),
    ],
)
def test_stream_supports_messages_and_updates_for_v1_and_v2(
    base_agent_module: Any,
    stream_mode: str,
    version: str,
    chunk_factory: Any,
    expected: list[str],
) -> None:
    graph = _FakeGraph(stream_chunks=chunk_factory(base_agent_module))
    agent = _agent_with_graph(base_agent_module, graph)

    result = list(agent.stream("current", stream_mode=stream_mode, version=version))

    assert result == expected
    assert graph.stream_call is not None
    assert graph.stream_call["stream_mode"] == stream_mode
    assert graph.stream_call["version"] == version
    assert graph.stream_call["input"]["messages"][-1].content == "current"

@pytest.mark.parametrize(
    ("stream_mode", "version", "chunk_factory", "expected"),
    [
        (
            "messages",
            "v1",
            lambda module: [(module.AIMessage(content="async messages v1"), {})],
            ["async messages v1"],
        ),
        (
            "messages",
            "v2",
            lambda module: [
                {
                    "type": "messages",
                    "ns": (),
                    "data": (_TokenWithContentBlocks("async messages v2"), {}),
                }
            ],
            ["async messages v2"],
        ),
        (
            "updates",
            "v1",
            lambda module: [
                {"agent": {"messages": [module.AIMessage(content="async updates v1")]}}
            ],
            ["async updates v1"],
        ),
        (
            "updates",
            "v2",
            lambda module: [
                {
                    "type": "updates",
                    "ns": (),
                    "data": {
                        "agent": {
                            "messages": [
                                module.AIMessage(content="async updates v2")
                            ]
                        }
                    },
                }
            ],
            ["async updates v2"],
        ),
    ],
)
def test_astream_supports_messages_and_updates_for_v1_and_v2(
    base_agent_module: Any,
    stream_mode: str,
    version: str,
    chunk_factory: Any,
    expected: list[str],
) -> None:
    graph = _FakeGraph(astream_chunks=chunk_factory(base_agent_module))
    agent = _agent_with_graph(base_agent_module, graph)

    async def collect() -> list[str]:
        return [
            chunk
            async for chunk in agent.astream(
                "current", stream_mode=stream_mode, version=version
            )
        ]

    result = asyncio.run(collect())

    assert result == expected
    assert graph.astream_call is not None
    assert graph.astream_call["stream_mode"] == stream_mode
    assert graph.astream_call["version"] == version
    assert graph.astream_call["input"]["messages"][-1].content == "current"
