"""
Analysis API endpoints (Part1 §2.1-2.7)。

R2 Three-Question Self-Check:
1. Contract Closure: 每个 endpoint 对应文档 §2 的一节；Service 层抛出的
   异常类型被映射为对应的 HTTP 状态码 (400/404/422)，异常->响应闭环。
2. Symmetry: POST /create 与 DELETE /{task_id} 对称；SSE 流在订阅者退出
   时通过 TaskManager 的 finally 块清理队列，资源对称释放。
3. External Timing: POST /create 先 db.commit 后再 submit 异步任务，确保
   SSE 订阅者读到任务时记录已落库；取消任务先 task_manager.cancel 后再
   更新数据库状态，避免异步管道继续写入已取消的记录。
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.task_manager import TaskManager
from app.api.deps import get_task_manager, get_analysis_service
from app.schemas.common import BaseResponse
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisCreateData,
    AnalysisTaskDetail,
    AnalysisListData,
    AnalysisListItem,
    AnalysisReportData,
    AnalysisTagsData,
    BloggerInfo,
    CancelTaskData,
    DeleteTaskData,
    Dimension,
    SubDimension,
    TagItem,
)
from app.services.task_service import (
    TaskService,
    TaskNotFoundError,
    TaskValidationError,
    TaskStateError,
    CookieRequiredError,
    ReportNotReadyError,
)
from app.services.cookie_service import CookieService
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _get_cookie_service() -> CookieService:
    return CookieService()


def _get_task_service(
    db: Session = Depends(get_db),
    task_manager: TaskManager = Depends(get_task_manager),
    cookie_service: CookieService = Depends(_get_cookie_service),
) -> TaskService:
    return TaskService(db, task_manager, cookie_service)


# ---------- POST /create ----------

@router.post("/create", response_model=BaseResponse[AnalysisCreateData])
async def create_analysis_task(
    payload: AnalysisCreateRequest,
    task_service: TaskService = Depends(_get_task_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    task_manager: TaskManager = Depends(get_task_manager),
):
    try:
        task = await task_service.create_task(
            blogger_url=payload.blogger_url,
            platform=payload.platform,
            analysis_level=payload.analysis_level,
            custom_config=payload.custom_config,
        )
    except TaskValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CookieRequiredError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 异步启动管道；TaskManager 保底会发出 complete/error 事件
    await task_manager.submit(task.id, analysis_service.run_analysis(task.id))

    return BaseResponse(
        code=0,
        message="success",
        data=AnalysisCreateData(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at,
        ),
    )


# ---------- GET /list ----------
# 注意：固定路径 /list 必须声明在动态路径 /{task_id} 之前，
# 否则 FastAPI 会把 "list" 当作 task_id 匹配到 GET /{task_id}。

@router.get("/list", response_model=BaseResponse[AnalysisListData])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query("all", alias="status"),
    task_service: TaskService = Depends(_get_task_service),
):
    items, total = task_service.list_tasks(page=page, page_size=page_size, status=status_filter)

    list_items: list[AnalysisListItem] = []
    for t in items:
        blogger = task_service.get_blogger_info(t.id)
        blogger_info = None
        if blogger:
            blogger_info = BloggerInfo(
                nickname=blogger.nickname,
                avatar_url=blogger.avatar_url,
                follower_count=blogger.follower_count,
            )
        list_items.append(
            AnalysisListItem(
                task_id=t.id,
                platform=t.platform,
                blogger_info=blogger_info,
                analysis_level=t.analysis_level,
                status=t.status,
                progress=t.progress,
                created_at=t.created_at,
                completed_at=t.completed_at,
                has_fragrance_session=task_service.has_fragrance_session(t.id),
            )
        )

    return BaseResponse(
        code=0,
        data=AnalysisListData(
            total=total,
            page=page,
            page_size=page_size,
            items=list_items,
        ),
    )


# ---------- GET /{task_id} ----------

@router.get("/{task_id}", response_model=BaseResponse[AnalysisTaskDetail])
async def get_task_details(
    task_id: str,
    task_service: TaskService = Depends(_get_task_service),
):
    try:
        task = task_service.get_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")

    blogger = task_service.get_blogger_info(task_id)
    blogger_info = None
    if blogger:
        blogger_info = BloggerInfo(
            nickname=blogger.nickname,
            avatar_url=blogger.avatar_url,
            follower_count=blogger.follower_count,
            platform=task.platform,
        )

    return BaseResponse(
        code=0,
        data=AnalysisTaskDetail(
            task_id=task.id,
            platform=task.platform,
            blogger_url=task.blogger_url,
            analysis_level=task.analysis_level,
            status=task.status,
            progress=task.progress,
            current_step=task.current_step,
            blogger_info=blogger_info,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            custom_config=task.custom_config,
            error_message=task.error_message,
        ),
    )


# ---------- GET /{task_id}/progress (SSE) ----------

@router.get("/{task_id}/progress")
async def stream_progress(
    task_id: str,
    task_service: TaskService = Depends(_get_task_service),
    task_manager: TaskManager = Depends(get_task_manager),
):
    # 先确认任务存在，避免 SSE 流被打开后才发现 404
    try:
        task_service.get_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        try:
            async for event in task_manager.subscribe(task_id):
                event_type = event.get("type", "message")
                data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except ValueError as e:
            # subscribe 检测到 not_found 时也会抛 ValueError
            err = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲
        },
    )


# ---------- POST /{task_id}/cancel ----------

@router.post("/{task_id}/cancel", response_model=BaseResponse[CancelTaskData])
async def cancel_task(
    task_id: str,
    task_service: TaskService = Depends(_get_task_service),
):
    try:
        task = await task_service.cancel_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BaseResponse(
        code=0,
        message="Task cancelled successfully",
        data=CancelTaskData(task_id=task.id, status=task.status),
    )


# ---------- GET /{task_id}/report ----------

@router.get("/{task_id}/report", response_model=BaseResponse[AnalysisReportData])
async def get_profile_report(
    task_id: str,
    task_service: TaskService = Depends(_get_task_service),
):
    try:
        task, report = task_service.get_report(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ReportNotReadyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    blogger = task_service.get_blogger_info(task_id)
    blogger_info = BloggerInfo(
        nickname=blogger.nickname if blogger else None,
        avatar_url=blogger.avatar_url if blogger else None,
        follower_count=blogger.follower_count if blogger else None,
        platform=task.platform,
    )

    report_dict = {
        "climate_consumption": report.climate_consumption,
        "fragrance_consumption": report.fragrance_consumption,
        "fashion_fragrance_map": report.fashion_fragrance_map,
        "lifestyle_scenario": report.lifestyle_scenario,
        "overall_summary": report.overall_summary,
    }

    return BaseResponse(
        code=0,
        data=AnalysisReportData(
            task_id=task_id,
            blogger_info=blogger_info,
            report=report_dict,
            full_report_markdown=report.full_report_markdown,
        ),
    )


# ---------- GET /{task_id}/tags ----------

@router.get("/{task_id}/tags", response_model=BaseResponse[AnalysisTagsData])
async def get_aggregated_tags(
    task_id: str,
    task_service: TaskService = Depends(_get_task_service),
):
    try:
        report = task_service.get_report_for_tags(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ReportNotReadyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dimensions = task_service.build_tags_dimensions(report)
    return BaseResponse(code=0, data=AnalysisTagsData(dimensions=dimensions))


# ---------- DELETE /{task_id} ----------

@router.delete("/{task_id}", response_model=BaseResponse[DeleteTaskData])
async def delete_analysis_task(
    task_id: str,
    task_service: TaskService = Depends(_get_task_service),
):
    try:
        task_service.delete_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 文档 §2.7 + e2e 约定的固定文案
    return BaseResponse(
        code=0,
        message="Task and associated media cleaned up successfully",
        data=DeleteTaskData(task_id=task_id, deleted=True),
    )
