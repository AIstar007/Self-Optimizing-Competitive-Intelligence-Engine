"""FastAPI router for report-related endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core.application import GenerateIntelligenceReportUseCase
from core.interfaces.api.models import (
    ReportGenerateRequest,
    ReportResponse,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerateRequest) -> ReportResponse:
    """
    Generate an intelligence report for a company.
    
    Args:
        request: Report generation request
        
    Returns:
        Generated report with sections
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        use_case = GenerateIntelligenceReportUseCase()
        response = await use_case.execute(request.company_id, request.report_type)
        
        return ReportResponse(
            success=True,
            report_id=response.report_id,
            report_type=request.report_type,
            content=response.content,
            sections=response.sections,
            word_count=response.word_count,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/company/{company_id}", response_model=list[ReportResponse])
async def list_company_reports(
    company_id: str,
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(20, ge=1, le=100, description="Result limit"),
) -> list[ReportResponse]:
    """
    List all reports for a company.
    
    Args:
        company_id: Company ID
        report_type: Optional report type filter
        limit: Maximum results
        
    Returns:
        List of reports
    """
    try:
        # TODO: Implement report listing from repository
        return []
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str) -> ReportResponse:
    """
    Get a specific report.
    
    Args:
        report_id: Report ID
        
    Returns:
        Report details
    """
    try:
        # TODO: Implement report retrieval
        return ReportResponse(
            success=True,
            report_id=report_id,
            report_type="",
            content="",
            sections={},
            word_count=0,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Report not found")


@router.get("/{report_id}/section/{section_name}")
async def get_report_section(report_id: str, section_name: str):
    """
    Get a specific section of a report.
    
    Args:
        report_id: Report ID
        section_name: Section name
        
    Returns:
        Section content
    """
    try:
        # TODO: Implement section retrieval
        return {"report_id": report_id, "section": section_name, "content": ""}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Section not found")


@router.post("/schedule")
async def schedule_report(
    company_id: str = Query(..., description="Company ID"),
    report_type: str = Query("COMPETITIVE_ANALYSIS", description="Report type"),
    frequency: str = Query("weekly", description="Schedule frequency"),
):
    """
    Schedule a recurring report.
    
    Args:
        company_id: Company ID
        report_type: Type of report
        frequency: Schedule frequency
        
    Returns:
        Schedule confirmation
    """
    try:
        # TODO: Implement report scheduling
        return {
            "success": True,
            "company_id": company_id,
            "report_type": report_type,
            "frequency": frequency,
            "scheduled": True,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """
    Delete a report.
    
    Args:
        report_id: Report to delete
        
    Returns:
        Success status
    """
    try:
        # TODO: Implement report deletion
        return {"success": True, "report_id": report_id, "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{report_id}/export")
async def export_report(
    report_id: str,
    format: str = Query("pdf", description="Export format"),
):
    """
    Export a report in specified format.
    
    Args:
        report_id: Report to export
        format: Export format (pdf, docx, html)
        
    Returns:
        Export details
    """
    try:
        # TODO: Implement report export
        return {
            "success": True,
            "report_id": report_id,
            "format": format,
            "url": f"/downloads/reports/{report_id}.{format}",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
