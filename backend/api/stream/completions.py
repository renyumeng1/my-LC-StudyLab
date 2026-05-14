"""
stream/completions.py — 回复补全模块
=====================================
这是你应该第六个写的文件，依赖：core.models.get_chat_model。

你需要写的函数：
  - needs_completion(text: str) -> bool
  - complete_response(question: str, current_reply: str) -> str
"""

# ============================================================
# 函数 1：needs_completion（你需要写的）
# ============================================================
# 作用：判断 AI 回复是否可能不完整，需要调用 LLM 补充。
#
# 返回 True 的条件（任一满足即可）：
#   1. 文本为空
#   2. 文本去空格后长度 < 30 字符
#   3. 文本末尾不是中文句号、感叹号、问号，也不是英文 . ! ?
#
# 提示：用 str.strip() 去空格，用 str.endswith(tuple) 检查结尾。
#
# 自己写 ↓↓↓


def needs_completion(text: str) -> bool:
    """
    判断回复文本是否不完整，需要补全。
    返回 True = 需要补全，False = 已经完整。
    """
    # TODO: 三步判断 — 空、太短、结尾不是标点
    raise NotImplementedError("请实现 needs_completion")


# ============================================================
# 函数 2：complete_response（你需要写的）
# ============================================================
# 作用：调用 LLM（get_chat_model()）补充不完整的回复。
#
# 参数：
#   - question: 用户原始问题
#   - current_reply: 当前不完整的 AI 回复
#
# 返回：LLM 生成的补充文本（字符串），失败返回空字符串 ""。
#
# 提示：
#   - from core.models import get_chat_model
#   - model = get_chat_model()
#   - 构造一个 prompt，让模型基于问题和当前回复继续回答
#   - await model.ainvoke([{"role": "user", "content": prompt}])
#   - 用 getattr(completion, "content", "") 获取回复文本
#
# 自己写 ↓↓↓


async def complete_response(question: str, current_reply: str) -> str:
    """
    让 LLM 基于用户问题和不完整回复，生成补充内容。
    返回补充文本，失败返回空字符串。
    """
    # TODO: from core.models import get_chat_model
    # TODO: 构造 prompt
    # TODO: await model.ainvoke(...)
    # TODO: 返回 getattr(completion, "content", "") or ""
    raise NotImplementedError("请实现 complete_response")
