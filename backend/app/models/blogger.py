"""
Blogger Profile, Post, Comment, and Commenter Profile database models.

R2 Three-Question Self-Check:
1. Contract Closure: ForeignKey defines ondelete="CASCADE" to mirror database-level cascade constraints.
2. Symmetry: Pure data definitions representing scraped social media items. No ephemeral resources.
3. External Timing: Database writes are scoped to specific parent tasks, preventing cross-task timing/race issues.
"""

from sqlalchemy import Column, String, Integer, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class BloggerProfile(Base):
    __tablename__ = "blogger_profiles"
    
    id = Column(String(36), primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    platform_uid = Column(String(100), nullable=False)
    nickname = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=True)
    age = Column(String(20), nullable=True)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    signature = Column(Text, nullable=True)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    total_favorited = Column(Integer, default=0)
    aweme_count = Column(Integer, default=0)
    avatar_url = Column(String(512), nullable=True)
    raw_data = Column(JSON, nullable=False)
    
    task = relationship("AnalysisTask", back_populates="blogger_profile")


class BloggerPost(Base):
    __tablename__ = "blogger_posts"
    
    id = Column(String(36), primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    aweme_id = Column(String(100), nullable=False)
    title = Column(Text, nullable=True)
    desc = Column(Text, nullable=True)
    create_time = Column(Integer, nullable=False)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    cover_url = Column(String(512), nullable=True)
    video_url = Column(String(512), nullable=True)
    local_cover_path = Column(String(512), nullable=True)
    local_video_path = Column(String(512), nullable=True)
    raw_data = Column(JSON, nullable=False)
    
    task = relationship("AnalysisTask", back_populates="posts")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String(36), primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    aweme_id = Column(String(100), nullable=False)
    cid = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=False)
    nickname = Column(String(100), nullable=True)
    text = Column(Text, nullable=False)
    create_time = Column(Integer, nullable=False)
    digg_count = Column(Integer, default=0)
    reply_comment_total = Column(Integer, default=0)
    raw_data = Column(JSON, nullable=False)
    
    task = relationship("AnalysisTask", back_populates="comments")


class CommenterProfile(Base):
    __tablename__ = "commenter_profiles"
    
    id = Column(String(36), primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    platform_uid = Column(String(100), nullable=False)
    nickname = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=True)
    age = Column(String(20), nullable=True)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    signature = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    raw_data = Column(JSON, nullable=False)
    
    task = relationship("AnalysisTask", back_populates="commenters")
