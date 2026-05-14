"""
stream/suggestions.py — 后续问题建议生成器
==========================================
这是你应该第七个写的文件，依赖：core.models.get_chat_model。

你需要写的函数：
  - generate_suggestions(question: str, reply: str) -> list[str]
"""

import json
import logging

logger = logging.getLogger(__name__)


# ============================================================
# 函数：generate_suggestions（你需要写的）
# ============================================================
# 作用：根据用户问题 + AI 最终回复，让 LLM 生成 ≤4 条后续可点
#       击的问题建议。
#
# 参数：
#   - question: 用户原始问题
#   - reply:    最终的 AI 回复全文
#
# 返回：字符串列表，每条 ≤30 字，最多 4 条。失败返回空列表 []。
#
# 实现步骤：
#   1. from core.models import get_chat_model
#   2. 构造 prompt，要求 LLM 以 JSON 数组格式返回
#   3. await model.ainvoke(...)
#   4. 解析 JSON 数组
#   5. 过滤：每项转 str、去空格、去重、截取前 4 条
#   6. 整个包在 try/except 中，任何异常返回 []
#
# Prompt 参考：
#   "你是一个辅助对话的助手。请根据以下用户问题和最终回复，
#    生成4条简洁、相关、可点击的后续问题建议。
#    用JSON数组返回，每个元素是不超过30字的中文字符串，
#    不要包含编号或多余文本。\n\n
#    用户问题：{question}\n\n
#    最终回复：{reply}"
#
# 自己写 ↓↓↓


async def generate_suggestions(question: str, reply: str) -> list[str]:
    """
    基于对话内容，让 LLM 生成后续问题建议。
    返回 ≤4 条建议的列表，失败返回 []。
    """
    # TODO: 1. 获取 model
    # TODO: 2. 构造 prompt
    # TODO: 3. model.ainvoke
    # TODO: 4. json.loads 解析
    # TODO: 5. 过滤、截取前 4 条
    # TODO: 6. try/except 包裹
    raise NotImplementedError("请实现 generate_suggestions")
