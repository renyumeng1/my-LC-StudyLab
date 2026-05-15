from __future__ import annotations

import asyncio
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...config import get_logger
from ...workflows.study_flow_graph import (
    start_study_flow,
    submit_answers,
    get_workflow_state,
    get_workflow_history,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])


class StartWorkflowRequest(BaseModel):
    user_question: str = Field(..., min_length=1, description="用户学习问题")
    index_name: str = Field(..., min_length=1, description="用于检索的索引名称")
    thread_id: Optional[str] = Field(default=None, description="线程 ID")


class SubmitAnswersRequest(BaseModel):
    answers: dict[str, Any] = Field(..., description="用户提交的答案")


class WorkflowStateResponse(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    thread_id: str = Field(..., description="线程 ID")
    state: Optional[dict[str, Any]] = Field(default=None, description="当前状态")


class WorkflowHistoryResponse(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    thread_id: str = Field(..., description="线程 ID")
    history: list[dict[str, Any]] = Field(default_factory=list, description="历史记录")


@router.post("/start", response_model=WorkflowStateResponse)
async def start_workflow(request: StartWorkflowRequest) -> WorkflowStateResponse:
    thread_id = request.thread_id or str(uuid4())
    try:
        if request.thread_id:
            existing = await asyncio.to_thread(get_workflow_state, thread_id)
            if existing:
                return WorkflowStateResponse(
                    success=False,
                    error="thread_id 已存在，请使用新的 thread_id",
                    thread_id=thread_id,
                )
        state = await asyncio.to_thread(
            start_study_flow, request.user_question, thread_id, request.index_name
        )
        return WorkflowStateResponse(thread_id=thread_id, state=state)
    except Exception as exc:
        logger.error(f"❌ 启动工作流失败: {exc}")
        return WorkflowStateResponse(success=False, error=str(exc), thread_id=thread_id)


@router.post("/{thread_id}/answers", response_model=WorkflowStateResponse)
async def submit_workflow_answers(
    thread_id: str, request: SubmitAnswersRequest
) -> WorkflowStateResponse:
    try:
        state = await asyncio.to_thread(submit_answers, thread_id, request.answers)
        return WorkflowStateResponse(thread_id=thread_id, state=state)
    except Exception as exc:
        logger.error(f"❌ 提交答案失败: {exc}")
        return WorkflowStateResponse(success=False, error=str(exc), thread_id=thread_id)


@router.get("/{thread_id}/state", response_model=WorkflowStateResponse)
async def get_state(thread_id: str) -> WorkflowStateResponse:
    try:
        state = await asyncio.to_thread(get_workflow_state, thread_id)
        if not state:
            return WorkflowStateResponse(
                success=False, error="线程不存在", thread_id=thread_id
            )
        return WorkflowStateResponse(thread_id=thread_id, state=state)
    except Exception as exc:
        logger.error(f"❌ 获取状态失败: {exc}")
        return WorkflowStateResponse(success=False, error=str(exc), thread_id=thread_id)


@router.get("/{thread_id}/history", response_model=WorkflowHistoryResponse)
async def get_history(thread_id: str) -> WorkflowHistoryResponse:
    try:
        history = await asyncio.to_thread(get_workflow_history, thread_id)
        if history is None:
            return WorkflowHistoryResponse(
                success=False, error="线程不存在", thread_id=thread_id
            )
        return WorkflowHistoryResponse(thread_id=thread_id, history=history)
    except Exception as exc:
        logger.error(f"❌ 获取历史失败: {exc}")
        return WorkflowHistoryResponse(
            success=False, error=str(exc), thread_id=thread_id
        )
