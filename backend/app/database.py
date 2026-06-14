"""
Database connection and session creation settings.

R2 Three-Question Self-Check:
1. Contract Closure: get_db ensures session closure in the finally block.
2. Symmetry: Database sessions are opened and properly closed in a pair.
3. External Timing: Uses check_same_thread=False for SQLite compatibility in multi-threaded environment.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

db_url = settings.DATABASE_URL

# Normalize relative path to absolute path relative to BASE_DIR for Git Worktree compatibility
if db_url.startswith("sqlite:///./"):
    relative_path = db_url.replace("sqlite:///./", "")
    absolute_path = settings.BASE_DIR / relative_path
    db_url = f"sqlite:///{absolute_path}"

if db_url.startswith("sqlite:///"):
    db_file_path = db_url.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(os.path.abspath(db_file_path)), exist_ok=True)

connect_args = {}
if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
