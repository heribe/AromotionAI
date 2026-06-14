"""
PlatformCookie database model.

R2 Three-Question Self-Check:
1. Contract Closure: Fields have strict SQL constraints and default values.
2. Symmetry: Data representation, no dynamic resources allocated.
3. External Timing: Uses timezone-aware UTC timestamps for database operations.
"""

import datetime
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from app.database import Base


def _utcnow() -> datetime.datetime:
    """Timezone-aware UTC now; replaces deprecated datetime.datetime.utcnow()."""
    return datetime.datetime.now(datetime.timezone.utc)


class PlatformCookie(Base):
    __tablename__ = "platform_cookies"

    id = Column(String(36), primary_key=True, index=True) # UUID
    platform = Column(String(50), unique=True, nullable=False, index=True) # "douyin" | "xiaohongshu" | "taobao"
    cookie_data = Column(JSON, nullable=False) # Browser cookie JSON array
    is_valid = Column(Boolean, default=True, nullable=False)
    last_checked_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    uploaded_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=True)
