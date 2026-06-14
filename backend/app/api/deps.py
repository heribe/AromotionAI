"""
API dependencies injection module.
"""
from app.database import get_db
from app.core import TaskManager, task_manager

def get_task_manager() -> TaskManager:
    return task_manager
