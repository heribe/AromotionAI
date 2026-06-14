"""
Fragrance Recommendation Session and Chat Message database models.

R2 Three-Question Self-Check:
1. Contract Closure: Relationships are enforced using foreign keys with CASCADE delete constraints.
2. Symmetry: Deleting a session cascadingly cleans up all its associated chat messages (cascade="all, delete-orphan").
3. External Timing: Messages are appended sequentially in time order, stored inside sequential database transactions.
"""

import datetime
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class FragranceSession(Base):
    __tablename__ = "fragrance_sessions"
    
    id = Column(String(36), primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), nullable=True)
    selected_tags = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False) # Final recommended perfume formula list
    status = Column(String(20), default="generating", nullable=False) # "generating" | "completed" | "error"
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    task = relationship("AnalysisTask", back_populates="fragrance_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("fragrance_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False) # "user", "assistant"
    content = Column(Text, nullable=False)
    updated_plans = Column(JSON, nullable=True) # Modified perfume formula in the conversation
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    session = relationship("FragranceSession", back_populates="messages")
