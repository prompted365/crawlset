"""
Main FastAPI application for the intelligence pipeline backend.

Provides REST API endpoints for web extraction, webset management,
and content monitoring with proper async support.
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..config import get_settings
from ..database import get_db_manager, init_database
from .routes.analytics import router as analytics_router
from .routes.crawl import router as crawl_router
from .routes.enrichments import router as enrichments_router
from .routes.export import router as export_router
from .routes.extract import router as extract_router
from .routes.extraction import router as extraction_router
from .routes.monitors import router as monitors_router
from .routes.search import router as search_router
from .routes.tools import router as tools_router
from .routes.websets import router as websets_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    settings = get_settings()
    logger.info("Starting intelligence pipeline backend...")
    logger.info(f"Database URL: {settings.database_url}")

    # Initialize database
    db_manager = init_database(
        database_url=settings.database_url,
        echo=settings.database_echo,
    )
    await db_manager.init_db()
    logger.info("Database initialized successfully")

    # Initialize RuVector client
    from ..ruvector.client import RuVectorClient

    ruvector_client = RuVectorClient(ruvector_url=settings.ruvector_url)
    try:
        await ruvector_client.initialize()
        app.state.ruvector_client = ruvector_client
        logger.info(f"RuVector client connected to {settings.ruvector_url}")
    except Exception as e:
        logger.warning(f"RuVector client init failed (service may not be running): {e}")
        app.state.ruvector_client = ruvector_client  # Store anyway for lazy init

    yield

    # Shutdown
    logger.info("Shutting down intelligence pipeline backend...")

    # Close RuVector client
    if hasattr(app.state, "ruvector_client") and app.state.ruvector_client:
        await app.state.ruvector_client.close()
        logger.info("RuVector client closed")

    await db_manager.close()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Intelligence Pipeline API",
    description="Production-grade web extraction and monitoring system",
    version="1.0.0",
    lifespan=lifespan,
)

# Get settings
settings = get_settings()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with logging."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred",
                "status_code": 500,
            }
        },
    )


# Health check endpoint
@app.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns the application status and version information.
    """
    result = {
        "status": "healthy",
        "version": "1.0.0",
        "database": "unknown",
        "ruvector": "unknown",
    }

    # Check database connectivity
    try:
        db_manager = get_db_manager()
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT 1"))
        result["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        result["database"] = "disconnected"
        result["status"] = "degraded"

    # Check RuVector connectivity
    try:
        from fastapi import Request as _Req

        ruvector_client = getattr(app.state, "ruvector_client", None)
        if ruvector_client:
            health = await ruvector_client.health_check()
            result["ruvector"] = health.get("status", "connected")
        else:
            result["ruvector"] = "not_initialized"
    except Exception as e:
        logger.error(f"RuVector health check failed: {e}", exc_info=True)
        result["ruvector"] = "disconnected"
        result["status"] = "degraded"

    return result


# API routers
app.include_router(websets_router, prefix="/api/websets", tags=["websets"])
app.include_router(extraction_router, prefix="/api/extraction", tags=["extraction"])
app.include_router(monitors_router, prefix="/api/monitors", tags=["monitors"])
app.include_router(enrichments_router, prefix="/api/enrichments", tags=["enrichments"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(export_router, prefix="/api/export", tags=["export"])
# Legacy routes (keep for backward compatibility)
app.include_router(crawl_router, prefix="/crawl", tags=["crawl"])
app.include_router(extract_router, prefix="/extract", tags=["extract"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
