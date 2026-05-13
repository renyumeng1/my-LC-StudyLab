"""
聊天 API 路由
提供 /chat 接口，支持流式和非流式对话

这是第 1 阶段的 API 接口，实现：
1. POST /chat - 非流式对话
2. POST /chat/stream - 流式对话（SSE）
3. 支持对话历史管理
4. 支持不同的 Agent 模式
"""

from typing import Optional,Any
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
import json
import asyncio
import time



from ...agent import create_base_agent
from ...core.tools import BASIC_TOOLS,WEB_SEARCH_TOOLS,WEATHER_TOOLS
from ...config import settings,get_logger


logger = get_logger(__name__)


router = APIRouter(prefix="/chat",tags=["chat"])


# ==================== 请求/响应模型 ====================