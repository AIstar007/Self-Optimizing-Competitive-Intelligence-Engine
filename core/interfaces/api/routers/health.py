"""FastAPI router for health checks and system status."""

from fastapi import APIRouter
from core.interfaces.api.models import HealthResponse, StatsResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "api": "operational",
            "database": "operational",
            "llm": "operational",
            "browser": "operational",
            "cache": "operational",
        },
    )


@router.get("/ready", response_model=dict)
async def readiness_check() -> dict:
    """
    Readiness probe endpoint.
    
    Returns:
        Readiness status
    """
    return {
        "ready": True,
        "timestamp": "",
    }


@router.get("/alive", response_model=dict)
async def liveness_check() -> dict:
    """
    Liveness probe endpoint.
    
    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "timestamp": "",
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """
    Get system statistics.
    
    Returns:
        System stats
    """
    return StatsResponse(
        total_companies=0,
        total_signals=0,
        total_reports=0,
        active_workflows=0,
        api_calls=0,
    )


@router.get("/info")
async def get_info() -> dict:
    """
    Get system information.
    
    Returns:
        System info
    """
    return {
        "name": "Self-Optimizing Competitive Intelligence Engine",
        "version": "1.0.0",
        "description": "AI-powered competitive intelligence system",
        "api_version": "1.0.0",
        "supported_agents": [
            "research",
            "analysis",
            "strategy",
            "report",
            "critique",
            "planner",
        ],
        "supported_workflows": [
            "competitive_intelligence",
            "market_analysis",
            "competitor_tracking",
        ],
    }


@router.get("/version")
async def get_version() -> dict:
    """
    Get version information.
    
    Returns:
        Version info
    """
    return {
        "version": "1.0.0",
        "api_version": "1.0.0",
    }
