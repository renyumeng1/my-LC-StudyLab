"""
stream/generator.py — SSE 流式生成器（核心拼装）
================================================
这是你应该最后（第八个）写的文件，因为它依赖上面所有模块。

这是整个 stream 包的核心：把之前写的所有小函数拼装成一个
完整的 async generator，被 chat.py 的路由调用。

你需要写的函数：
  - generate_stream(request: ChatRequest) -> AsyncGenerator[str, None]
"""

import asyncio
import logging

from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

from ..routers.chat import ChatRequest, get_tools_for_request, convert_chat_history
from ...agent import create_base_agent
from ...core.tools import WEATHER_TOOLS

from .events import sse_event
from ...core.usage_tracker import UsageTracker
from .extractors import extract_tool_call_info, extract_reasoning
from .finders import (
    find_final_ai_message,
    find_weather_tool_result,
    find_any_tool_result,
)
from .completions import needs_completion, complete_response
from .suggestions import generate_suggestions
from .utils import lcp_len

logger = logging.getLogger(__name__)


# ============================================================
# 函数：generate_stream（你需要写的 — 核心拼装）
# ============================================================
# 这是整个 stream 包的主函数，被 chat.py 调用。
#
# 整体流程（对照你之前看到的原始代码，去掉 DeepResearch）：
#
#   try:
#     ① yield sse_event("start", message="开始生成...")
#
#     ② usage_tracker = UsageTracker()
#
#     ③ tools = get_tools_for_request(request.use_tools, request.use_advanced_tools)
#        weather_tool_names = {t.name for t in WEATHER_TOOLS}
#        agent = create_base_agent(tools=tools, prompt_mode=request.mode)
#
#     ④ messages = convert_chat_history(request.chat_history)
#        messages.append(HumanMessage(content=request.message))
#        graph_input = {"messages": messages}
#
#     ⑤ tool_calls_map = {}     # {tool_id: tool_info}
#        current_content = ""    # 已发送的累积文本
#        all_messages = []       # 所有消息
#        tool_call_count = {}    # 工具调用次数
#
#     ⑥ config = {"recursion_limit": 50}
#        async for chunk in agent.graph.astream(graph_input, config=config,
#                                                stream_mode="messages"):
#            # 解析 chunk → (message, metadata)
#            # usage_tracker.update_from_metadata(metadata)
#            # all_messages.append(message)
#
#            # --- 如果是 AIMessage ---
#            #   → extract_tool_call_info 处理 tool_calls
#            #   → lcp_len 增量发送文本 chunk
#            #   → extract_reasoning 提取推理过程
#
#            # --- 如果是 ToolMessage ---
#            #   → 更新 tool_calls_map 中的状态和结果
#            #   → 如果是天气工具结果，直接推送给用户
#
#            await asyncio.sleep(0.01)
#
#     ⑦ final_msg = find_final_ai_message(all_messages)
#        兜底：如果没有最终 AI 消息，尝试用工具结果替代
#        （先用 find_weather_tool_result，再用 find_any_tool_result）
#
#     ⑧ if needs_completion(current_content):
#            extra = await complete_response(request.message, current_content)
#            if extra: yield sse_event("chunk", content=extra)
#
#     ⑨ suggestions = await generate_suggestions(request.message, current_content)
#        if suggestions: yield sse_event("suggestions", data=suggestions)
#
#     ⑩ yield sse_event("context", data=usage_tracker.get_usage_info())
#        yield sse_event("end", message="生成完成")
#        usage_tracker.log_summary()
#
#   except Exception as e:
#       yield sse_event("error", message="处理出错", error=str(e))
#
# 提示：
#   - 每个 yield 后不要忘记 await asyncio.sleep(0.01) 让出控制权
#   - tool_calls_map 的 key 是 tool_call["id"]，用于后续 ToolMessage 更新
#   - 天气工具结果可以直接 sse_event("chunk", ...) 推送给用户
#     （避免等待模型再总结一次）
#
# 自己写 ↓↓↓


async def generate_stream(request: ChatRequest):
    """
    SSE 流式生成器（主函数）。
    接收 ChatRequest，产生 SSE 事件字符串序列。
    """
    # TODO: 按照上面 ①~⑩ 的流程，调用之前写的所有小函数
    raise NotImplementedError("请实现 generate_stream")
