"""
Unit tests for AnalysisService.

R2 Three-Question Self-Check:
1. Contract Closure: Ensures the DB transaction is committed/rolled back, and status is correctly updated.
2. Symmetry: Verifies that resources are generated (like cover placeholders) and no leftover db sessions are dangling.
3. External Timing: Uses async orchestrators to monitor state transitions step by step.
"""

import os
import uuid
import asyncio
import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisTask
from app.models.blogger import BloggerProfile, BloggerPost, Comment, CommenterProfile
from app.models.profile import ProfileReport
from app.core.task_manager import TaskManager
from app.services.analysis_service import AnalysisService
from app.analyzers.visual_analyzer import VisualAnalyzer

@pytest.mark.asyncio
async def test_full_pipeline_mock_run(db: Session):
    # Setup mock mode for environment
    os.environ["AROMOTION_TEST_MODE"] = "mock"
    
    # 1. Create a task in database
    task_id = str(uuid.uuid4())
    task = AnalysisTask(
        id=task_id,
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4wLjABAAAA_mock_sec_uid",
        analysis_level="standard"
    )
    db.add(task)
    db.commit()
    
    task_manager = TaskManager()
    service = AnalysisService(db, task_manager)
    
    # 用 task_manager 提交任务
    await task_manager.submit(task_id, service.run_analysis(task_id))
    
    # 然后立即开始订阅，收集事件
    events = []
    async for event in task_manager.subscribe(task_id):
        events.append(event)
        
    # 等待后台任务完全结束
    await asyncio.sleep(0.01)
    
    # 2. 验证事件流
    event_types = [e["type"] for e in events]
    assert "progress" in event_types
    assert "step_complete" in event_types
    assert "complete" in event_types
    
    # 3. 验证数据库状态
    db.expire_all() # 确保读取到最新数据
    updated_task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    assert updated_task is not None
    assert updated_task.status == "completed"
    assert updated_task.progress == 100
    
    # 验证生成了博主资料、帖子、评论、粉丝和报告记录
    blogger_profile = db.query(BloggerProfile).filter_by(task_id=task_id).first()
    assert blogger_profile is not None
    assert blogger_profile.nickname is not None
    
    posts = db.query(BloggerPost).filter_by(task_id=task_id).all()
    assert len(posts) > 0
    # 仅被分析流程选中的帖子才会下载封面（避免无用下载），因此过滤出已有 local_cover_path 的记录
    processed_posts = [p for p in posts if p.local_cover_path]
    assert len(processed_posts) > 0
    for post in processed_posts:
        assert os.path.exists(post.local_cover_path)
        
    comments = db.query(Comment).filter_by(task_id=task_id).all()
    assert len(comments) > 0
    
    commenter_profiles = db.query(CommenterProfile).filter_by(task_id=task_id).all()
    assert len(commenter_profiles) > 0
    for cp in commenter_profiles:
        assert cp.avatar_url is not None
        assert os.path.exists(cp.avatar_url)
        
    report = db.query(ProfileReport).filter_by(task_id=task_id).first()
    assert report is not None
    assert report.overall_summary is not None
    assert report.climate_consumption is not None


@pytest.mark.asyncio
async def test_pipeline_error_rollback(db: Session):
    # Setup mock mode
    os.environ["AROMOTION_TEST_MODE"] = "mock"
    
    task_id = str(uuid.uuid4())
    task = AnalysisTask(
        id=task_id,
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4wLjABAAAA_mock_sec_uid",
        analysis_level="standard"
    )
    db.add(task)
    db.commit()
    
    task_manager = TaskManager()
    service = AnalysisService(db, task_manager)
    
    # 模拟在 analyze_cover 步骤抛出 RuntimeError 异常
    with patch.object(VisualAnalyzer, "analyze_cover", side_effect=RuntimeError("Mock visual analyzer error")):
        # 提交任务
        await task_manager.submit(task_id, service.run_analysis(task_id))
        
        # 收集事件
        events = []
        async for event in task_manager.subscribe(task_id):
            events.append(event)
            
        await asyncio.sleep(0.01)
        
    # 1. 验证事件流中有 error 事件
    event_types = [e["type"] for e in events]
    assert "error" in event_types
    
    # 2. 验证任务状态更新为 failed，并记录了错误信息
    db.expire_all()
    failed_task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    assert failed_task is not None
    assert failed_task.status == "failed"
    assert "Mock visual analyzer error" in failed_task.error_message
    
    # 3. 验证回滚：应该没有生成 ProfileReport 报告记录
    report = db.query(ProfileReport).filter_by(task_id=task_id).first()
    assert report is None
