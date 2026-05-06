from typing import AsyncIterator, Iterator, Literal, Optional, Sequence, Any, cast
from langchain.agents import AgentState, create_agent
from langchain.chat_models import BaseChatModel
from langchain.messages import AIMessage, AnyMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from langgraph.types import StreamMode
from langchain_core.runnables import RunnableConfig


from ..core.model import get_chat_model, get_streaming_model
from ..core.prompts import get_system_prompt, get_prompt_with_tools
from ..core.tools import ALL_TOOLS, BASIC_TOOLS

from ..config import settings, get_logger

logger = get_logger(__name__)


class BaseAgent:
    """Agent基类封装langchain的create_agent"""

    # NOTE:这里的model可以是一个字符串，也可以是一个BaseLanguageModel对象，如果是字符串，就会被ChatOpenAI识别为模型名称，创建一个ChatOpenAI对象；如果是BaseLanguageModel对象，就直接使用这个对象作为模型。
    def __init__(
        self,
        model: Optional[str | BaseLanguageModel] = None,
        tools: Optional[Sequence[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        prompt_mode: str = "default",
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        初始化 Base Agent


        Args:
            model: LLM 模型，可以是：
                   - 字符串标识符（如 "openai:gpt-4o"）
                   - BaseChatModel 实例
                   如果为 None，使用默认配置创建
            tools: Agent 可用的工具列表（Sequence[BaseTool]）
                   如果为 None 或空列表，Agent 将只包含模型节点，不进行工具调用循环
            system_prompt: 自定义系统提示词
                          如果为 None，则根据 prompt_mode 生成
            prompt_mode: 提示词模式（default/coding/research/concise/detailed）
            debug: 是否启用详细日志（对应 create_agent 的 debug 参数）
            **kwargs: 其他传递给 create_agent 的参数，如：
                     - checkpointer: 状态持久化
                     - store: 跨线程数据存储
                     - interrupt_before/interrupt_after: 中断点
                     - name: Agent 名称
        """
        if model is None:
            self.model = f"openai:{settings.model_name}"
            logger.info(f"🤖 使用默认模型: {self.model}")

        elif isinstance(model, str):
            self.model = model
            logger.info(f"🤖 使用指定模型: {self.model}")

        # ==================== 工具初始化 ====================
        if tools is None:
            # 默认使用基础工具集（不需要 API Key）
            self.tools = BASIC_TOOLS
            logger.info(f"🔧 使用基础工具集 ({len(self.tools)} 个工具)")
        else:
            self.tools = list(tools) if tools else []
            logger.info(f"🔧 使用自定义工具集 ({len(self.tools)} 个工具)")

        # 打印工具列表
        if self.tools:
            tool_names = [tool.name for tool in self.tools]
            logger.debug(f"   工具列表: {', '.join(tool_names)}")

        # ==================== 提示词初始化 ====================
        if system_prompt is None:
            if self.tools:
                self.system_prompt = get_prompt_with_tools(mode=prompt_mode)
                logger.info(f"📝 使用带工具说明的系统提示词 (模式: {prompt_mode})")

            else:
                self.system_prompt = get_system_prompt(mode=prompt_mode)
                logger.info(f"📝 使用基础系统提示词 (模式: {prompt_mode})")

        else:
            self.system_prompt = system_prompt
            logger.info(f"📝 使用自定义系统提示词")

        self.debug = debug

        try:
            logger.info(f"🚀 使用langchain V1.2 create_agent API...")
            self.graph = create_agent(
                model=self.model,
                tools=self.tools if self.tools else None,
                system_prompt=self.system_prompt,
                debug=self.debug,
                **kwargs,
            )

            logger.info("✅ Agent 创建成功（CompiledStateGraph）")
            logger.debug(f"   配置: debug={self.debug}, tools={len(self.tools)}")

        except Exception as e:
            logger.error(f"❌ Agent 创建失败: {e}")
            raise

    @staticmethod
    def _iter_text_parts(message: Any) -> Iterator[str]:
        message_obj = cast(Any, message)
        content_blocks = getattr(message_obj, "content_blocks", None)

        if content_blocks:
            found_text = False
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        found_text = True
                        yield text
            if found_text:
                return

        content = getattr(message_obj, "content", None)
        if not content:
            return

        if isinstance(content, str):
            yield content
            return

        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    yield item
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str) and text:
                        yield text
            return

        yield str(content)

    @staticmethod
    def _iter_update_messages(update: Any) -> Iterator[Any]:
        if not isinstance(update, dict):
            return

        messages = update.get("messages")
        if isinstance(messages, list):
            yield from messages
        elif messages:
            yield messages

        for node_update in update.values():
            if not isinstance(node_update, dict):
                continue
            messages = node_update.get("messages")
            if isinstance(messages, list):
                yield from messages
            elif messages:
                yield messages

    @staticmethod
    def _iter_latest_ai_text_from_update(update: Any) -> Iterator[str]:
        messages = list(BaseAgent._iter_update_messages(update))
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                yield from BaseAgent._iter_text_parts(message)
                return

    @staticmethod
    def _iter_message_text_from_chunk(chunk: Any) -> Iterator[str]:
        message = None

        if isinstance(chunk, tuple) and len(chunk) == 2:
            message, metadata = chunk
        elif isinstance(chunk, AIMessage):
            message = chunk
        elif isinstance(chunk, dict) and chunk.get("type") == "messages":
            data = chunk.get("data")
            if isinstance(data, tuple) and len(data) == 2:
                message, metadata = data

        if message is not None:
            yield from BaseAgent._iter_text_parts(message)

    @staticmethod
    def _iter_update_text_from_chunk(chunk: Any) -> Iterator[str]:
        update = chunk
        if isinstance(chunk, dict) and chunk.get("type") == "updates":
            update = chunk.get("data")

        yield from BaseAgent._iter_latest_ai_text_from_update(update)

    def invoke(
        self,
        input_text: str,
        chat_history: Optional[list[BaseMessage]] = None,
        **kwargs: Any,
    ) -> str:
        """
        同步调用 Agent（非流式）
        使用 {"messages": [...]} 作为输入格式。

        Args:
            input_text: 用户输入的文本
            chat_history: 对话历史（可选）
            **kwargs: 其他传递给 graph 的参数

        Returns:
            Agent 的响应文本

        Example:
            >>> agent = BaseAgent()
            >>> response = agent.invoke("你好，请介绍一下自己")
            >>> print(response)
        """

        logger.info(f"🚀 执行 Agent 调用: {input_text[:50]}...")

        try:

            messages = []

            if chat_history:
                messages.extend(chat_history)

            messages.append(HumanMessage(content=input_text))

            graph_input: dict[str, Any] = {"messages": messages}
            graph_input.update(kwargs)

            result = self.graph.invoke(cast(Any, graph_input))

            output_msgs = result.get("messages", [])

            ai_response: str = ""

            for msg in reversed(output_msgs):
                if isinstance(msg, AIMessage):
                    content = msg.content

                    if isinstance(content, str):
                        ai_response = content
                    else:
                        ai_response = str(content)
                    break

            logger.info(f"✅ Agent 调用成功，响应长度: {len(ai_response)}")
            logger.debug(f"   响应内容: {ai_response[:200]}...")

            return ai_response

        except Exception as e:
            error_msg = f"Agent 执行失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return f"抱歉，处理您的请求时出现错误: {str(e)}"

    def stream(
        self,
        input_text: str,
        chat_history: Optional[list[BaseMessage]] = None,
        stream_mode: StreamMode = "messages",
        version: Literal["v1", "v2"] = "v2",
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        流式调用 Agent

        默认使用 "messages" 模式，逐步返回消息内容。

        Args:
            input_text: 用户输入的文本
            chat_history: 对话历史（可选）
            stream_mode: 流式模式，可选值：
                        - "messages": 流式返回消息内容（推荐）
                        - "updates": 返回状态更新
                        - "values": 返回完整状态值
            version: 流式输出版本，"v1" 直接返回模式数据，"v2" 返回 {"type", "ns", "data"} 包装
            **kwargs: 其他参数

        Yields:
            Agent 输出的文本片段

        Example:
            >>> agent = BaseAgent()
            >>> for chunk in agent.stream("讲个笑话"):
            ...     print(chunk, end="", flush=True)

        """
        logger.info(f"🌊 执行 Agent 流式调用: {input_text[:50]}...")

        try:

            messages = []

            if chat_history:
                messages.extend(chat_history)

            messages.append(HumanMessage(content=input_text))

            graph_input = {"messages": messages}
            graph_input.update(kwargs)

            for chunk in self.graph.stream(
                input=cast(Any, graph_input),
                stream_mode=stream_mode,
                version=version,
            ):
                if stream_mode == "messages":
                    for content in self._iter_message_text_from_chunk(chunk):
                        logger.debug(f"   流式输出: {content[:50]}...")
                        yield content

                elif stream_mode == "updates":
                    for content in self._iter_update_text_from_chunk(chunk):
                        logger.debug(f"   流式输出: {content[:50]}...")
                        yield content

        except Exception as e:
            error_msg = f"Agent 流式执行失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            yield f"\n\n抱歉，处理您的请求时出现错误: {str(e)}"

    async def ainvoke(
        self,
        input_text: str,
        chat_history: Optional[list[BaseMessage]] = None,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> str:
        """
        异步调用 Agent

        Args:
            input_text: 用户输入的文本
            chat_history: 对话历史（可选）
            config: 其他配置参数（可选）
            **kwargs: 其他传递给 graph 的参数

        """
        logger.info(f"🚀 执行 Agent 异步调用: {input_text[:50]}...")

        try:
            messages = []
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))

            # 准备输入
            graph_input = {"messages": messages}
            graph_input.update(kwargs)

            result = await self.graph.ainvoke(cast(Any, graph_input), config=config)

            output_msgs = result.get("messages", [])

            ai_response: str = ""

            for msg in reversed(output_msgs):
                if isinstance(msg, AIMessage):
                    content = msg.content

                    if isinstance(content, str):
                        ai_response = content
                    else:
                        ai_response = str(content)
                    break

            logger.info(f"✅ Agent 异步调用成功，响应长度: {len(ai_response)}")

            return ai_response
        except Exception as e:
            error_msg = f"Agent 异步执行失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return f"抱歉，处理您的请求时出现错误: {str(e)}"

    async def astream(
        self,
        input_text: str,
        chat_history: Optional[list[BaseMessage]] = None,
        stream_mode: StreamMode = "messages",
        version: Literal["v1", "v2"] = "v2",
        **kwargs: Any,
    ) -> AsyncIterator[str | list[str | dict]]:
        """
        异步流式调用 Agent

        Args:
            input_text: 用户输入的文本
            chat_history: 对话历史（可选）
            stream_mode: 流式模式（"messages" 或 "updates"）
            version: 流式输出版本，"v1" 直接返回模式数据，"v2" 返回 {"type", "ns", "data"} 包装
            **kwargs: 其他参数

        Yields:
            Agent 输出的文本片段

        Example:
            >>> agent = BaseAgent()
            >>> async for chunk in agent.astream("讲个笑话"):
            ...     print(chunk, end="", flush=True)
        """
        logger.info(f"🌊 执行 Agent 异步流式调用: {input_text[:50]}...")

        try:
            # 准备消息列表
            messages = []
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))

            # 准备输入
            graph_input = {"messages": messages}
            graph_input.update(kwargs)

            # 异步流式执行 Graph
            async for chunk in self.graph.astream(
                cast(Any, graph_input), stream_mode=stream_mode, version=version
            ):
                # 根据 stream_mode 处理不同的输出格式
                if stream_mode == "messages":
                    for content in self._iter_message_text_from_chunk(chunk):
                        yield content

                elif stream_mode == "updates":
                    for content in self._iter_update_text_from_chunk(chunk):
                        yield content

            logger.info("✅ Agent 异步流式调用完成")

        except Exception as e:
            error_msg = f"Agent 异步流式执行失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            yield f"\n\n抱歉，处理您的请求时出现错误: {str(e)}"


def create_base_agent(
    model: Optional[str | BaseChatModel] = None,
    tools: Optional[Sequence[BaseTool]] = None,
    prompt_mode: str = "default",
    debug: bool = False,
    **kwargs: Any,
) -> BaseAgent:
    """
    创建基础 Agent 的便捷工厂函数

    根据 LangChain V1.2 的规范创建 Agent。

    Args:
        model: LLM 模型（字符串标识符或实例）
        tools: 工具列表
        prompt_mode: 提示词模式
        debug: 是否启用调试日志
        **kwargs: 其他参数（传递给 create_agent）

    Returns:
        配置好的 BaseAgent 实例

    Example:
        >>> # 创建默认 Agent
        >>> agent = create_base_agent()
        >>>
        >>> # 创建编程助手 Agent
        >>> agent = create_base_agent(prompt_mode="coding")
        >>>
        >>> # 创建带所有工具的 Agent
        >>> from core.tools import ALL_TOOLS
        >>> agent = create_base_agent(tools=ALL_TOOLS)
        >>>
        >>> # 使用特定模型
        >>> agent = create_base_agent(model="openai:gpt-4o-mini")

    """
    logger.info(f"🏭 创建 Base Agent (mode={prompt_mode}, debug={debug})")

    return BaseAgent(
        model=model,
        tools=tools,
        prompt_mode=prompt_mode,
        debug=debug,
        **kwargs,
    )


if __name__ == "__main__":
    # 简单测试
    agent = create_base_agent()
    # response = agent.invoke("你好，请介绍一下自己")
    # print("Agent 响应:", response)

    for chunk in agent.stream("讲个笑话", version="v1"):
        print(chunk, end="", flush=True)
