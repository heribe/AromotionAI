"""
API V1 router registration module.
"""

from fastapi import APIRouter
from app.api.v1.cookies import router as cookies_router
from app.api.v1.analysis import router as analysis_router

api_router = APIRouter()
api_router.include_router(cookies_router)
api_router.include_router(analysis_router)
