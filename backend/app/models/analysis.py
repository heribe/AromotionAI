"""
AnalysisTask database model.

R2 Three-Question Self-Check:
1. Contract Closure: Cascade deletes are handled via SQLAlchemy database relationships (cascade="all, delete-orphan").
2. Symmetry: Task lifecycle flows through a clear status state machine.
3. External Timing: Uses datetime.datetime.utcnow for created_at, updated_at, and completed_at.
"""

import datetime
from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"
    
    id = Column(String(36), primary_key=True, index=True) # UUID
    user_id = Column(String(36), nullable=True) # Set to None for the first version
    platform = Column(String(50), nullable=False) # "douyin"
    blogger_url = Column(String(512), nullable=False)
    analysis_level = Column(String(20), nullable=False) # "quick", "standard", "deep", "custom"
    custom_config = Column(JSON, nullable=True)
    status = Column(String(20), default="pending", nullable=False) # "pending", "collecting", "analyzing", "waiting_tags", "processing", "completed", "failed"
    progress = Column(Integer, default=0, nullable=False) # 0-100
    current_step = Column(String(100), default="准备开始", nullable=False)
    error_message = Column(String(512), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Cascade relationship: delete all related scraped and analysis data when task is deleted
    blogger_profile = relationship("BloggerProfile", uselist=False, back_populates="task", cascade="all, delete-orphan")
    posts = relationship("BloggerPost", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    commenters = relationship("CommenterProfile", back_populates="task", cascade="all, delete-orphan")
    profile_report = relationship("ProfileReport", uselist=False, back_populates="task", cascade="all, delete-orphan")
    fragrance_sessions = relationship("FragranceSession", back_populates="task", cascade="all, delete-orphan")
