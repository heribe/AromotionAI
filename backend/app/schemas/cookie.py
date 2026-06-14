"""
Cookie module specific Pydantic Schemas.

R2 Three-Question Self-Check:
1. Contract Closure: Enforces input validation structure for cookies (JSON lists of CookieItems) and formats dates for responses.
2. Symmetry: Schema layer behaves as data validation contracts; no temporary files or resources are requested.
3. External Timing: DTO models without concurrent synchronization concerns.
"""

import datetime
from pydantic import BaseModel, Field

class CookieItem(BaseModel):
    name: str = Field(..., description="Cookie key name")
    value: str = Field(..., description="Cookie value")
    domain: str | None = Field(None, description="Domain scope")
    path: str | None = Field(None, description="Path scope")
    expires: float | None = Field(None, description="Expiry timestamp")
    httpOnly: bool | None = Field(None)
    secure: bool | None = Field(None)
    sameSite: str | None = Field(None)

class CookieUploadResponse(BaseModel):
    platform: str = Field(..., description="Platform name, e.g., 'douyin'")
    is_valid: bool = Field(..., description="Whether the cookie status is currently valid")
    uploaded_at: datetime.datetime = Field(..., description="Upload timestamp")

class CookieStatusItem(BaseModel):
    platform: str = Field(..., description="Platform name")
    is_valid: bool = Field(...)
    uploaded_at: datetime.datetime | None = Field(None, description="Upload timestamp; None when not configured")
    last_checked_at: datetime.datetime | None = Field(None)

class CookieStatusResponse(BaseModel):
    cookies: list[CookieStatusItem] = Field(..., description="List of cookie statuses for all supported platforms")
