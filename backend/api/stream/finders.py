"""
stream/finders.py — 消息与工具结果查找器
=========================================
这是你应该第五个写的文件，依赖：langchain_core.messages。

你需要写的函数：
  - find_final_ai_message(all_messages: list) -> AIMessage | None
  - find_weather_tool_result(tool_calls_map: dict) -> str | None
  - find_any_tool_result(tool_calls_map: dict) -> str | None
"""

from langchain_core.messages import AIMessage

# 天气类工具名称集合（用于优先匹配）
WEATHER_TOOL_NAMES = {"get_daily_weather", "get_weather_forecast", "get_weather"}


# ============================================================
# 函数 1：find_final_ai_message（你需要写的）
# ============================================================
# 作用：从所有消息列表中反向查找最后一条有实质文本内容的 AIMessage。
#       用于在流式循环结束后确定"最终回复"是什么。
#
# 遍历策略：从后往前（reversed），找到第一条：
#   - isinstance(msg, AIMessage)
#   - msg.content 存在
#   - msg.content.strip() 非空字符串
#
# 返回：AIMessage 或 None
#
# 自己写 ↓↓↓


def find_final_ai_message(all_messages: list) -> AIMessage | None:
    """
    从消息列表中查找最后一条有实际内容的 AI 消息。
    从后往前遍历，返回第一个有非空 content 的 AIMessage。
    """
    # TODO: for msg in reversed(all_messages):
    # TODO:     如果 isinstance(msg, AIMessage) 且 content.strip() 非空 → return msg
    # TODO: return None
    raise NotImplementedError("请实现 find_final_ai_message")


# ============================================================
# 函数 2：find_weather_tool_result（你需要写的）
# ============================================================
# 作用：在 tool_calls_map 中优先查找天气工具的成功结果。
#       tool_calls_map 结构：{tool_id: {"name": ..., "state": ..., "result": ...}}
#
# 条件：
#   - tool_info["name"] 在 WEATHER_TOOL_NAMES 中
#   - tool_info["state"] == "output-available"
#   - tool_info["result"] 非空
#
# 返回：结果字符串 或 None
#
# 自己写 ↓↓↓


def find_weather_tool_result(tool_calls_map: dict) -> str | None:
    """
    在工具调用结果中优先查找天气工具的成功结果。
    遍历 tool_calls_map，返回第一个匹配的天气工具结果。
    """
    # TODO: 遍历 tool_calls_map.values()
    # TODO: 检查 name 是否在 WEATHER_TOOL_NAMES 中、state 是否为 "output-available"、result 是否存在
    # TODO: return tool_info["result"] 或 None
    raise NotImplementedError("请实现 find_weather_tool_result")


# ============================================================
# 函数 3：find_any_tool_result（你需要写的）
# ============================================================
# 作用：兜底函数 — 找任意一个成功执行并返回结果的工具输出。
#       如果没找到天气工具结果，用这个做最后的 fallback。
#
# 条件：同 find_weather_tool_result，但不限制工具名称。
#
# 自己写 ↓↓↓


def find_any_tool_result(tool_calls_map: dict) -> str | None:
    """
    兜底查找 — 返回第一个有成功结果的工具输出（不限工具名）。
    """
    # TODO: 遍历 tool_calls_map.values()
    # TODO: 检查 state 是否为 "output-available" 且 result 非空
    # TODO: return tool_info["result"] 或 None
    raise NotImplementedError("请实现 find_any_tool_result")
