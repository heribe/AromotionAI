"""
Fragrance recommendation API endpoints (Part2 §2.1-2.5)。

R2 Three-Question Self-Check:
1. Contract Closure: 每个 endpoint 对应文档 §2 的一节；Service 层抛出的
   异常类型被映射为对应的 HTTP 状态码 (400/404/422/500/502)。
2. Symmetry: POST /generate 创建 session，GET /{session_id} 读取，
   POST /regenerate 覆盖并清空 chat；资源生命周期由 service 层管理。
3. External Timing: generate 是长时 AI 调用，service 层先落 generating
   态再调引擎，避免客户端超时后 session 处于不确定状态。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import BaseResponse
from app.schemas.fragrance import (
    GenerateRequest,
    GenerateData,
    ChatRequest,
    ChatData,
    RegenerateRequest,
    SessionDetailData,
    ChatHistoryData,
)
from app.services.fragrance_service import (
    FragranceService,
    SessionNotFoundError,
    SessionStateError,
    TaskNotCompletedError,
    TagsValidationError,
    FragranceEngineError,
)
from app.services.task_service import TaskNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fragrance", tags=["Fragrance"])


def get_fragrance_service(db: Session = Depends(get_db)) -> FragranceService:
    """DI 工厂：默认使用 PromptFragranceEngine。测试可通过
    app.dependency_overrides 注入 mock engine。"""
    return FragranceService(db)


# ---------- POST /generate ----------

@router.post("/generate", response_model=BaseResponse[GenerateData])
async def generate_recommendations(
    payload: GenerateRequest,
    service: FragranceService = Depends(get_fragrance_service),
):
    try:
        data = await service.generate(payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskNotCompletedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TagsValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FragranceEngineError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return BaseResponse(code=0, data=data)


# ---------- GET /{session_id} ----------
# 注意：固定子路径（/history）必须在动态 {session_id} 之前不会被吞，
# FastAPI 按 {session_id} + 一级子路径匹配，/history 与 /{session_id}/history
# 不会冲突（前者无 session_id 段）。此处只需保证 /{session_id} 声明在
# /generate 之后即可。

@router.get("/{session_id}", response_model=BaseResponse[SessionDetailData])
async def get_session_detail(
    session_id: str,
    service: FragranceService = Depends(get_fragrance_service),
):
    try:
        data = service.get_session_detail(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Fragrance session not found")

    return BaseResponse(code=0, data=data)


# ---------- GET /{session_id}/history ----------

@router.get("/{session_id}/history", response_model=BaseResponse[ChatHistoryData])
async def get_chat_history(
    session_id: str,
    service: FragranceService = Depends(get_fragrance_service),
):
    try:
        data = service.get_history(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Fragrance session not found")

    return BaseResponse(code=0, data=data)


# ---------- POST /{session_id}/chat ----------

@router.post("/{session_id}/chat", response_model=BaseResponse[ChatData])
async def chat_with_session(
    session_id: str,
    payload: ChatRequest,
    service: FragranceService = Depends(get_fragrance_service),
):
    try:
        data = await service.chat(session_id, payload.message)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Fragrance session not found")
    except SessionStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FragranceEngineError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return BaseResponse(code=0, data=data)


# ---------- POST /{session_id}/regenerate ----------

@router.post("/{session_id}/regenerate", response_model=BaseResponse[GenerateData])
async def regenerate_recommendations(
    session_id: str,
    payload: RegenerateRequest,
    service: FragranceService = Depends(get_fragrance_service),
):
    try:
        data = await service.regenerate(session_id, payload)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Fragrance session not found")
    except SessionStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TagsValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FragranceEngineError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return BaseResponse(code=0, data=data)
