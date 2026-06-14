"""
Analysis API Pydantic schemas (Part1 §2 接口契约).

R2 Three-Question Self-Check:
1. Contract Closure: Each request/response schema maps 1:1 to a documented API
   contract in docs/01-part1-backend.md §2.1-2.7. URL/level validation raises
   clean ValueError that the API layer translates to 400/422.
2. Symmetry: Pure DTO models, no resources to acquire/release.
3. External Timing: Stateless validation; safe for concurrent requests.
"""

import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


SUPPORTED_PLATFORMS = {"douyin", "xiaohongshu", "taobao"}
PRESET_LEVELS = {"quick", "standard", "deep"}


class AnalysisCreateRequest(BaseModel):
    """POST /api/v1/analysis/create 请求体（§2.1）。"""

    blogger_url: str = Field(..., description="博主主页 URL，必须以 http 开头")
    platform: str = Field("auto", description="平台：douyin/xiaohongshu/taobao/auto")
    analysis_level: str = Field("standard", description="quick/standard/deep/custom")
    custom_config: Optional[dict[str, Any]] = Field(
        None, description="自定义配置，仅 analysis_level=custom 时必填"
    )

    @field_validator("blogger_url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.startswith("http"):
            raise ValueError("Invalid blogger URL format")
        return v


class AnalysisCreateData(BaseModel):
    task_id: str
    status: str = "pending"
    created_at: datetime.datetime


class BloggerInfo(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    follower_count: Optional[int] = None
    platform: Optional[str] = None


class AnalysisTaskDetail(BaseModel):
    """GET /api/v1/analysis/{task_id} 响应 data（§2.2）。"""

    task_id: str
    platform: str
    blogger_url: str
    analysis_level: str
    status: str
    progress: int
    current_step: str
    blogger_info: Optional[BloggerInfo] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    custom_config: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


class AnalysisListItem(BaseModel):
    task_id: str
    platform: str
    blogger_info: Optional[BloggerInfo] = None
    analysis_level: str
    status: str
    progress: int
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    has_fragrance_session: bool = False


class AnalysisListData(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AnalysisListItem]


class AnalysisReportData(BaseModel):
    """GET /api/v1/analysis/{task_id}/report 响应 data（§2.4）。"""

    task_id: str
    blogger_info: BloggerInfo
    report: dict[str, Any]
    full_report_markdown: str


class TagItem(BaseModel):
    name: str
    percentage: float
    is_default_selected: bool = False
    mutually_exclusive_group: Optional[str] = None


class SubDimension(BaseModel):
    sub_id: str
    sub_name: str
    tags: list[TagItem]
    is_mutually_exclusive: bool = False
    max_select: Optional[int] = None


class Dimension(BaseModel):
    dimension_id: str
    dimension_name: str
    sub_dimensions: list[SubDimension]


class AnalysisTagsData(BaseModel):
    """GET /api/v1/analysis/{task_id}/tags 响应 data（§2.5）。"""

    dimensions: list[Dimension]


class CancelTaskData(BaseModel):
    task_id: str
    status: str = "cancelled"


class DeleteTaskData(BaseModel):
    task_id: str
    deleted: bool = True
