"""Main FastAPI application for the Competitive Intelligence Engine."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from core.interfaces.api.routers import (
    signals,
    reports,
    markets,
    competitors,
    workflows,
    agents,
    companies,
    tasks,
    health,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Competitive Intelligence Engine API")
    logger.info("Services initializing...")
    yield
    # Shutdown
    logger.info("Shutting down Competitive Intelligence Engine API")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Competitive Intelligence Engine API",
        description="AI-powered competitive intelligence system with autonomous agents",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ========================================================================
    # Middleware Configuration
    # ========================================================================

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Gzip compression middleware
    app.add_middleware(GZIPMiddleware, minimum_size=1000)

    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # In production, specify trusted hosts
    )

    # ========================================================================
    # Exception Handlers
    # ========================================================================

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": str(exc) if logger.level == logging.DEBUG else None,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors."""
        logger.warning(f"Value error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": str(exc)},
        )

    # ========================================================================
    # Request/Response Hooks
    # ========================================================================

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log HTTP requests and responses."""
        logger.debug(f"{request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"Response: {response.status_code}")
        return response

    # ========================================================================
    # Router Registration
    # ========================================================================

    # Health and status endpoints
    app.include_router(health.router)

    # API v1 routes
    api_v1_prefix = "/api/v1"

    # Core business endpoints
    app.include_router(signals.router, prefix=api_v1_prefix)
    app.include_router(reports.router, prefix=api_v1_prefix)
    app.include_router(markets.router, prefix=api_v1_prefix)
    app.include_router(competitors.router, prefix=api_v1_prefix)

    # Workflow and agent endpoints
    app.include_router(workflows.router, prefix=api_v1_prefix)
    app.include_router(agents.router, prefix=api_v1_prefix)

    # Management endpoints
    app.include_router(companies.router, prefix=api_v1_prefix)
    app.include_router(tasks.router, prefix=api_v1_prefix)

    # ========================================================================
    # Root Endpoint
    # ========================================================================

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "Competitive Intelligence Engine API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "redoc": "/api/redoc",
        }

    # ========================================================================
    # API Documentation Endpoints
    # ========================================================================

    @app.get("/api/endpoints")
    async def list_endpoints():
        """List all available API endpoints."""
        routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                routes.append(
                    {
                        "path": route.path,
                        "methods": list(route.methods),
                        "name": route.name,
                    }
                )
        return {"endpoints": routes, "total_count": len(routes)}

    return app


# Create application instance
app = create_app()

# ============================================================================
# Module-level startup/shutdown events
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("API startup: Initializing services")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("API shutdown: Cleaning up resources")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
    )
