"""
stream/events.py — SSE 事件格式化工具
======================================
这是你应该第二个写的文件，依赖：无。

你需要写的函数：
  - sse_event(event_type: str, **kwargs) -> str
"""

import json

# ============================================================
# 函数：sse_event（你需要写的）
# ============================================================
# 作用：把事件类型 + 键值对包装成 SSE（Server-Sent Events）协议格式。
#
# SSE 协议格式要求：
#   data: <JSON字符串>\n\n
#
# 每个事件的 JSON 中必须包含 "type" 字段，其余字段通过 **kwargs 传入。
#
# 示例：
#   sse_event("start", message="开始生成...")
#   → 'data: {"type": "start", "message": "开始生成..."}\\n\\n'
#
#   sse_event("chunk", content="你好")
#   → 'data: {"type": "chunk", "content": "你好"}\\n\\n'
#
# 提示：
#   - 用 json.dumps(dict, ensure_ascii=False) 避免中文被转义
#   - 返回的字符串末尾必须是两个换行符 \\n\\n
#
# 自己写 ↓↓↓


def sse_event(event_type: str, data:dict) -> str:
    """将事件类型和数据包装为 SSE 格式字符串"""
    # NOTE: 构建 payload 字典 {"type": event_type, **kwargs}
    payload = {
        "type":event_type,**data
    }
    # NOTE: json.dumps + 拼接 "data: " 前缀 + "\n\n" 后缀
    return f"data:{json.dumps(payload, ensure_ascii=False)}\n\n"
