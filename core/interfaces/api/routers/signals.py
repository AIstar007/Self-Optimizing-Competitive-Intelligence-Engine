"""FastAPI router for signal-related endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from core.application import SearchCompetitorSignalsUseCase
from core.interfaces.api.models import (
    SignalSearchRequest,
    SignalSearchResponse,
    SignalResponse,
)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/search", response_model=SignalSearchResponse)
async def search_signals(request: SignalSearchRequest) -> SignalSearchResponse:
    """
    Search for competitor signals.
    
    Args:
        request: Signal search request with filters
        
    Returns:
        SignalSearchResponse with matching signals
        
    Raises:
        HTTPException: If search fails
    """
    try:
        use_case = SearchCompetitorSignalsUseCase()
        response = await use_case.execute(request.company_id, request.keywords)
        
        signals = [
            SignalResponse(
                id=signal.id,
                title=signal.title,
                source=signal.source,
                severity=signal.severity,
                signal_type=signal.signal_type,
                verified=signal.verified,
                created_at=signal.created_at.isoformat(),
            )
            for signal in response.signals
        ]
        
        return SignalSearchResponse(
            success=True,
            signals=signals,
            total_count=len(response.signals),
            relevant_count=sum(1 for s in signals if s.severity in ["HIGH", "CRITICAL"]),
            sources=list(set(s.source for s in signals)),
            summary=response.summary,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/company/{company_id}", response_model=SignalSearchResponse)
async def get_company_signals(
    company_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    signal_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=500, description="Result limit"),
) -> SignalSearchResponse:
    """
    Get all signals for a company with optional filters.
    
    Args:
        company_id: Company ID
        severity: Optional severity filter
        signal_type: Optional signal type filter
        limit: Maximum results to return
        
    Returns:
        List of signals for the company
    """
    try:
        # TODO: Implement signal retrieval from repository
        return SignalSearchResponse(
            success=True,
            signals=[],
            total_count=0,
            relevant_count=0,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/competitor/{competitor_name}", response_model=SignalSearchResponse)
async def get_competitor_signals(
    competitor_name: str,
    days: int = Query(30, ge=1, le=365, description="Time range in days"),
) -> SignalSearchResponse:
    """
    Get recent signals about a competitor.
    
    Args:
        competitor_name: Competitor name
        days: Time range for signals
        
    Returns:
        Recent signals about the competitor
    """
    try:
        # TODO: Implement competitor signal retrieval
        return SignalSearchResponse(
            success=True,
            signals=[],
            total_count=0,
            relevant_count=0,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: str) -> SignalResponse:
    """
    Get details of a specific signal.
    
    Args:
        signal_id: Signal ID
        
    Returns:
        Signal details
    """
    try:
        # TODO: Implement signal detail retrieval
        return SignalResponse(
            id=signal_id,
            title="",
            source="",
            severity="",
            signal_type="",
            verified=False,
            created_at="",
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Signal not found")


@router.post("/{signal_id}/verify")
async def verify_signal(signal_id: str):
    """
    Verify a signal.
    
    Args:
        signal_id: Signal to verify
        
    Returns:
        Success status
    """
    try:
        # TODO: Implement signal verification
        return {"success": True, "signal_id": signal_id, "verified": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{signal_id}/enrich")
async def enrich_signal(signal_id: str):
    """
    Enrich a signal with additional data.
    
    Args:
        signal_id: Signal to enrich
        
    Returns:
        Enriched signal details
    """
    try:
        # TODO: Implement signal enrichment
        return {"success": True, "signal_id": signal_id, "enriched": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{signal_id}")
async def delete_signal(signal_id: str):
    """
    Delete a signal.
    
    Args:
        signal_id: Signal to delete
        
    Returns:
        Success status
    """
    try:
        # TODO: Implement signal deletion
        return {"success": True, "signal_id": signal_id, "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/batch/verify")
async def batch_verify_signals(signal_ids: list[str] = Query(...)):
    """
    Verify multiple signals.
    
    Args:
        signal_ids: List of signal IDs to verify
        
    Returns:
        Verification results
    """
    try:
        # TODO: Implement batch verification
        return {
            "success": True,
            "total": len(signal_ids),
            "verified": len(signal_ids),
            "results": [{"id": sid, "verified": True} for sid in signal_ids],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
