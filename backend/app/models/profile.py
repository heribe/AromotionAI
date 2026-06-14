"""
ProfileReport database model.

R2 Three-Question Self-Check:
1. Contract Closure: JSON columns are declared as nullable=False to ensure that structured label dimensions are always stored.
2. Symmetry: Data entity model without dynamic resource lifecycle.
3. External Timing: Stored after analysis completes, bound via transactional block mapping back to the analysis task.
"""

import datetime
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def _utcnow() -> datetime.datetime:
    """Timezone-aware UTC now; replaces deprecated datetime.datetime.utcnow()."""
    return datetime.datetime.now(datetime.timezone.utc)


class ProfileReport(Base):
    __tablename__ = "profile_reports"

    id = Column(String(36), primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Four-dimensional profiles stored as structured JSON
    climate_consumption = Column(JSON, nullable=False)
    fragrance_consumption = Column(JSON, nullable=False)
    fashion_fragrance_map = Column(JSON, nullable=False)
    lifestyle_scenario = Column(JSON, nullable=False)

    overall_summary = Column(Text, nullable=False)
    full_report_markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    task = relationship("AnalysisTask", back_populates="profile_report")
