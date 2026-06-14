"""
Fragrance recommendation API Pydantic schemas (Part2 §2.1-2.5 接口契约).

R2 Three-Question Self-Check:
1. Contract Closure: 每个请求/响应 schema 对应 docs/03-part2-backend.md §2.x
   的一节；权重与 plan_count 的边界校验在 Pydantic 层完成，service 层再做
   互斥组语义校验，形成双层防御。
2. Symmetry: 纯 DTO 模型，无资源生命周期；generate 与 regenerate 响应
   共用 GenerateData，chat 与 history 通过 updated_plans 字段对称回写。
3. External Timing: 无状态校验，并发安全；optional 字段全部有默认值，
   避免 None 传播到业务层。
"""

import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------- 请求模型 ----------

class GenerateRequest(BaseModel):
    """POST /api/v1/fragrance/generate 请求体（§2.1）。

    blogger_weight / audience_weight 为可调参数（§三.3 差异化策略），
    两者之和非 1 时由 service 层自动归一化并在 warnings 中提示。
    """

    task_id: str = Field(..., description="已完成的分析任务 ID")
    selected_tags: dict[str, Any] = Field(
        ..., description="调香师筛选后的标签集合（按维度组织）"
    )
    blogger_weight: float = Field(
        0.5, ge=0.0, le=1.0, description="博主画像融合权重（可调参数）"
    )
    audience_weight: float = Field(
        0.5, ge=0.0, le=1.0, description="粉丝画像融合权重（可调参数）"
    )
    plan_count: int = Field(3, ge=1, le=5, description="生成方案数量（1-5）")


class ChatRequest(BaseModel):
    """POST /api/v1/fragrance/{session_id}/chat 请求体（§2.2）。"""

    message: str = Field(..., min_length=1, description="调香师的追问或反馈")


class RegenerateRequest(BaseModel):
    """POST /api/v1/fragrance/{session_id}/regenerate 请求体（§2.3）。

    selected_tags 缺省时复用 session 既有的标签；其余可选参数同 generate。
    """

    selected_tags: Optional[dict[str, Any]] = Field(
        None, description="新的标签集合；缺省时复用 session 既有标签"
    )
    blogger_weight: float = Field(0.5, ge=0.0, le=1.0)
    audience_weight: float = Field(0.5, ge=0.0, le=1.0)
    plan_count: int = Field(3, ge=1, le=5)


# ---------- 嵌套数据模型 ----------

class NoteItem(BaseModel):
    """单个香材（前/中/后调）。changed 字段仅在 chat updated_plans 中出现。"""

    name: str
    description: str = ""
    reason: str = ""
    changed: Optional[bool] = None


class IcebergAnalysis(BaseModel):
    """冰山三层分析（§三.1）。三字段均为分析文字。"""

    surface: str = ""
    middle: str = ""
    deep: str = ""


class FragrancePlan(BaseModel):
    """单套香调推荐方案（§2.1）。iceberg_analysis 缺省时由 service 层用
    session 级别的共享分析补齐，保证字段稳定。"""

    plan_id: str
    name: str
    category: str = ""
    top_notes: list[NoteItem] = []
    middle_notes: list[NoteItem] = []
    base_notes: list[NoteItem] = []
    recommendation_reason: str = ""
    fragrance_story: str = ""


# ---------- 响应数据模型 ----------

class GenerateData(BaseModel):
    """POST /generate 与 POST /{session_id}/regenerate 响应 data（§2.1/§2.3）。"""

    session_id: str
    status: str = "completed"
    iceberg_analysis: IcebergAnalysis
    recommendations: list[FragrancePlan]
    warnings: list[str] = []


class ChatData(BaseModel):
    """POST /{session_id}/chat 响应 data（§2.2）。

    updated_plans 仅包含被修改的方案；纯咨询对话时为 None。
    """

    reply: str
    updated_plans: Optional[list[FragrancePlan]] = None
    message_id: str


class SessionDetailData(BaseModel):
    """GET /api/v1/fragrance/{session_id} 响应 data（§2.4）。"""

    session_id: str
    task_id: str
    selected_tags: dict[str, Any]
    iceberg_analysis: IcebergAnalysis
    recommendations: list[FragrancePlan]
    status: str
    created_at: datetime.datetime


class ChatMessageItem(BaseModel):
    """单条对话消息（§2.5 history）。"""

    id: str
    role: str
    content: str
    updated_plans: Optional[list[FragrancePlan]] = None
    created_at: datetime.datetime


class ChatHistoryData(BaseModel):
    """GET /api/v1/fragrance/{session_id}/history 响应 data（§2.5）。"""

    messages: list[ChatMessageItem]
