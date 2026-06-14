"""
FastAPI app entrypoint and initializations.

R2 Three-Question Self-Check:
1. Contract Closure: CORS configuration split is safe and supports standard string lists. A health endpoint is provided.
2. Symmetry: No complex asynchronous tasks requiring cleanup currently.
3. External Timing: Database table structures are created on startup before routing incoming requests.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api.v1.router import api_router

# Auto create DB tables for Milestone 1 prototype
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="AromotionAI Backend Service for Perfumers",
    version="0.1.0"
)

# CORS Middleware setup
if settings.CORS_ORIGINS:
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
