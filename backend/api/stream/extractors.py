"""
stream/extractors.py — 消息内容提取器
======================================
这是你应该第四个写的文件，依赖：需要了解 AIMessage 的结构。

你需要写的函数：
  - extract_tool_call_info(tool_call: dict) -> dict
  - extract_reasoning(message) -> dict | None
"""

# ============================================================
# 函数 1：extract_tool_call_info（你需要写的）
# ============================================================
# 作用：把 AIMessage.tool_calls 列表中单个元素的原始 dict 转成
#       结构化的 tool_info 字典，用于前端展示工具调用状态。
#
# 输入的 tool_call dict 结构（来自 AIMessage.tool_calls）：
#   {
#       "id": "call_abc123",
#       "name": "get_weather",
#       "args": {"city": "北京"}
#   }
#
# 输出的 tool_info dict 结构：
#   {
#       "id": "call_abc123",
#       "name": "get_weather",
#       "type": "tool-call-get_weather",       # "tool-call-" + 工具名
#       "state": "input-available",             # 固定值，表示参数已就绪
#       "parameters": {"city": "北京"},          # 来自 tool_call["args"]
#       "result": None,                         # 初始为 None，等工具返回后更新
#       "error": None,                          # 初始为 None
#   }
#
# 自己写 ↓↓↓


def extract_tool_call_info(tool_call: dict) -> dict:
    """从 AIMessage 的 tool_call 原始数据中提取结构化信息"""
    # TODO: 从 tool_call 中提取 id, name, args
    # TODO: 构建并返回标准 tool_info 字典
    raise NotImplementedError("请实现 extract_tool_call_info")


# ============================================================
# 函数 2：extract_reasoning（你需要写的）
# ============================================================
# 作用：从 AIMessage 中提取模型的"推理过程"（thinking/reasoning）。
#       部分模型（如 DeepSeek R1、OpenAI o1）会在响应中嵌入推理链。
#
# AIMessage 中可能包含推理内容的位置：
#   - message.additional_kwargs.get("reasoning_content")
#   - message.additional_kwargs.get("thinking")
#   - message.response_metadata 中的某些字段
#
# 如果找到推理内容，返回：
#   {"content": "推理文本...", "duration": 0}
# 如果没有，返回 None。
#
# 提示：duration 可以先写 0，后续如果有时间戳信息再改为实际耗时。
#
# 自己写 ↓↓↓


def extract_reasoning(message) -> dict | None:
    """
    从 AIMessage 中提取推理/思考过程。
    返回 {"content": str, "duration": float} 或 None。
    """
    # TODO: 检查 message.additional_kwargs 中的 reasoning_content / thinking 字段
    # TODO: 如果有内容，返回 {"content": ..., "duration": 0}
    # TODO: 没有则返回 None
    raise NotImplementedError("请实现 extract_reasoning")
