"""
API dependencies injection module.
"""
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core import TaskManager, task_manager
from app.services.analysis_service import AnalysisService

def get_task_manager() -> TaskManager:
    return task_manager

def get_analysis_service(
    db: Session = Depends(get_db),
    task_manager: TaskManager = Depends(get_task_manager)
) -> AnalysisService:
    return AnalysisService(db, task_manager)
