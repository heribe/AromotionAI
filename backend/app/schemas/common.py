"""
Common API schemas, specifying a unified response envelope.

R2 Three-Question Self-Check:
1. Contract Closure: BaseResponse defines the standard data contract (code, message, data) for all endpoints.
2. Symmetry: Pure DTO (Data Transfer Object) representations, no dynamic resources.
3. External Timing: Thread-safe, read-only structures after instantiation.
"""

from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    code: int = Field(0, description="Status code. 0 for success, non-zero for exceptions/errors.")
    message: str = Field("success", description="Feedback response message")
    data: T | None = Field(default=None, description="Actual response data payload")
