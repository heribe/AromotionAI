"""
Pytest configuration and fixtures.

R2 Three-Question Self-Check:
1. Contract Closure: Provides clean DB setup and teardown, dynamic test directory creation/deletion, and handles session isolation.
2. Symmetry: Symmetric setup/teardown (creates directories and deletes them afterwards), symmetric create_all/drop_all for database tables.
3. External Timing: Modifies settings configurations BEFORE importing database modules to avoid lazy initialization race conditions.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os
import shutil
from pathlib import Path

from app.config import settings

# Override settings configuration immediately to isolate testing DB and files
absolute_db_path = settings.BASE_DIR / "data/db/test_aromotion.db"
absolute_db_url = f"sqlite:///{absolute_db_path}"
absolute_cookie_dir = str(settings.BASE_DIR / "data/test_cookies")

settings.DATABASE_URL = absolute_db_url
settings.COOKIE_DIR = absolute_cookie_dir

# Import database and app AFTER overriding the settings
from app.database import Base, get_db
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    # Make sure parent directories exist
    os.makedirs(os.path.dirname(absolute_db_path), exist_ok=True)
    os.makedirs(absolute_cookie_dir, exist_ok=True)
    
    yield
    
    # Tear down global configurations
    if os.path.exists(absolute_cookie_dir):
        try:
            shutil.rmtree(absolute_cookie_dir)
        except OSError:
            pass
    if os.path.exists(absolute_db_path):
        try:
            os.remove(absolute_db_path)
        except OSError:
            pass

@pytest.fixture(scope="function")
def db():
    # Construct clean schema before each test case, drop after finished
    engine = create_engine(absolute_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
