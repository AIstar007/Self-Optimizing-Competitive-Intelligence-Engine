"""Webhook API router."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from datetime import datetime

from core.infrastructure.webhooks.webhook_manager import (
    get_webhook_manager,
    WebhookManager,
    WebhookEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class WebhookRequest(BaseModel):
    """Webhook registration request."""

    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="List of events to subscribe to")
    headers: Optional[dict] = Field(None, description="Custom headers")
    active: bool = Field(True, description="Whether webhook is active")
    description: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response."""

    id: str
    url: str
    events: List[str]
    headers: Optional[dict]
    active: bool
    secret: str
    created_at: datetime
    description: Optional[str]


class WebhookUpdateRequest(BaseModel):
    """Webhook update request."""

    url: Optional[str] = None
    events: Optional[List[str]] = None
    headers: Optional[dict] = None
    active: Optional[bool] = None
    description: Optional[str] = None


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery record."""

    id: str
    webhook_id: str
    event: str
    status: str
    response_status: Optional[int]
    error: Optional[str]
    attempt: int
    created_at: datetime


class WebhookStatsResponse(BaseModel):
    """Webhook statistics."""

    total_deliveries: int
    successful: int
    failed: int
    success_rate: float
    last_delivery: Optional[datetime]


@router.post("", response_model=WebhookResponse)
async def register_webhook(
    request: WebhookRequest,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Register a new webhook."""
    try:
        webhook = webhook_manager.register_webhook(
            url=request.url,
            events=request.events,
            headers=request.headers,
            active=request.active,
            description=request.description,
        )

        return {
            "id": webhook.id,
            "url": webhook.url,
            "events": webhook.events,
            "headers": webhook.headers,
            "active": webhook.active,
            "secret": webhook.secret,
            "created_at": webhook.created_at,
            "description": webhook.description,
        }
    except Exception as e:
        logger.error(f"Error registering webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    active_only: bool = Query(False, description="Only return active webhooks"),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> list:
    """List all webhooks."""
    try:
        webhooks = webhook_manager.list_webhooks()

        if active_only:
            webhooks = [w for w in webhooks if w.active]

        return [
            {
                "id": w.id,
                "url": w.url,
                "events": w.events,
                "headers": w.headers,
                "active": w.active,
                "secret": w.secret,
                "created_at": w.created_at,
                "description": w.description,
            }
            for w in webhooks
        ]
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Get webhook by ID."""
    try:
        webhook = webhook_manager.get_webhook(webhook_id)

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {
            "id": webhook.id,
            "url": webhook.url,
            "events": webhook.events,
            "headers": webhook.headers,
            "active": webhook.active,
            "secret": webhook.secret,
            "created_at": webhook.created_at,
            "description": webhook.description,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Update webhook."""
    try:
        webhook = webhook_manager.update_webhook(
            webhook_id=webhook_id,
            url=request.url,
            events=request.events,
            headers=request.headers,
            active=request.active,
            description=request.description,
        )

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {
            "id": webhook.id,
            "url": webhook.url,
            "events": webhook.events,
            "headers": webhook.headers,
            "active": webhook.active,
            "secret": webhook.secret,
            "created_at": webhook.created_at,
            "description": webhook.description,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Delete webhook."""
    try:
        success = webhook_manager.delete_webhook(webhook_id)

        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {"message": "Webhook deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(10, ge=1, le=100),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> list:
    """Get delivery history for webhook."""
    try:
        deliveries = webhook_manager.get_delivery_history(webhook_id, limit=limit)

        return [
            {
                "id": d.id,
                "webhook_id": d.webhook_id,
                "event": d.event,
                "status": d.status,
                "response_status": d.response_status,
                "error": d.error,
                "attempt": d.attempt,
                "created_at": d.created_at,
            }
            for d in deliveries
        ]
    except Exception as e:
        logger.error(f"Error getting deliveries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{webhook_id}/stats", response_model=WebhookStatsResponse)
async def get_webhook_stats(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Get webhook statistics."""
    try:
        stats = webhook_manager.get_webhook_stats(webhook_id)

        if not stats:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {
            "total_deliveries": stats.get("total_deliveries", 0),
            "successful": stats.get("successful", 0),
            "failed": stats.get("failed", 0),
            "success_rate": stats.get("success_rate", 0),
            "last_delivery": stats.get("last_delivery"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Test webhook delivery."""
    try:
        webhook = webhook_manager.get_webhook(webhook_id)

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Trigger test event
        await webhook_manager.trigger_event(WebhookEvent.ALERT_CREATED, {"test": True})

        return {
            "message": "Test event triggered",
            "webhook_id": webhook_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{webhook_id}/resend")
async def resend_webhook_delivery(
    webhook_id: str,
    delivery_id: str = Body(..., description="Delivery ID to resend"),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
) -> dict:
    """Resend failed webhook delivery."""
    try:
        webhook = webhook_manager.get_webhook(webhook_id)

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # This would need to be implemented in WebhookManager
        return {
            "message": "Resend requested",
            "webhook_id": webhook_id,
            "delivery_id": delivery_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending delivery: {e}")
        raise HTTPException(status_code=500, detail=str(e))
