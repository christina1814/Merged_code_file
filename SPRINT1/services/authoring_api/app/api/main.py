# app/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from services.authoring_api.app.api.routers import (
    fetch_routes,
    upload_routes,
    save_routes,
    delete_routes,
    autosave_routes
)
from services.authoring_api.app.utils.db import init_db, close_db, health_check
from services.authoring_api.app.common.observability.metrics import get_metrics_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for startup and shutdown.
    """
    # Startup
    print("[API] Starting Authoring API...")
    await init_db()  # Initialize async DB pool
    print("[API] ✅ Startup complete")
    
    yield
    
    # Shutdown
    print("[API] Shutting down Authoring API...")
    await close_db()  # Close async DB pool
    print("[API] ✅ Shutdown complete")


app = FastAPI(
    title="Authoring API",
    description="API for document authoring operations with observability",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(fetch_routes.router)
app.include_router(upload_routes.router)
app.include_router(save_routes.router)
app.include_router(delete_routes.router)
app.include_router(autosave_routes.router)


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "service": "authoring-api",
        "status": "healthy",
        "version": "1.0.0",
        "features": [
            "fetch",
            "upload",
            "save",
            "delete",
            "autosave"
        ]
    }


@app.get("/health")
async def health():
    """
    Detailed health check endpoint.
    Checks database connectivity.
    """
    db_healthy = await health_check()
    
    overall_status = "healthy" if db_healthy else "degraded"
    
    return {
        "service": "authoring-api",
        "status": overall_status,
        "version": "1.0.0",
        "checks": {
            "database": "connected" if db_healthy else "disconnected",
            "api": "running"
        }
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns all metrics in Prometheus text format for scraping.
    
    Available metrics:
    - authoring_blob_operations_total
    - authoring_blob_fetch_latency_ms
    - authoring_blob_save_latency_ms
    - authoring_blob_delete_latency_ms
    - authoring_upload_latency_ms
    - authoring_autosave_success_total
    - authoring_autosave_failure_total
    - authoring_conflict_events_total
    - authoring_autosave_latency_ms
    """
    return get_metrics_text()