"""Webhook management system for inbound and outbound events."""

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook event types."""

    ALERT_CREATED = "alert.created"
    ALERT_RESOLVED = "alert.resolved"
    KPI_UPDATED = "kpi.updated"
    METRIC_UPDATED = "metric.updated"
    SIGNAL_DETECTED = "signal.detected"
    REPORT_GENERATED = "report.generated"
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"
    SYNC_COMPLETED = "sync.completed"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class Webhook:
    """Webhook configuration."""

    webhook_id: str
    url: str
    events: List[WebhookEvent]
    is_active: bool = True
    secret: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    max_retries: int = 3
    timeout_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0


@dataclass
class WebhookDelivery:
    """Record of webhook delivery attempt."""

    delivery_id: str = field(default_factory=lambda: str(uuid4()))
    webhook_id: str = ""
    event_type: WebhookEvent = None
    payload: Dict[str, Any] = field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    success: bool = False
    attempt: int = 1
    max_attempts: int = 3
    next_retry: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "delivery_id": self.delivery_id,
            "webhook_id": self.webhook_id,
            "event_type": self.event_type.value if self.event_type else None,
            "success": self.success,
            "attempt": self.attempt,
            "response_status": self.response_status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class WebhookManager:
    """Manager for webhook registrations and deliveries."""

    def __init__(self):
        """Initialize webhook manager."""
        self.webhooks: Dict[str, Webhook] = {}
        self.deliveries: List[WebhookDelivery] = []
        self.retry_queue: List[WebhookDelivery] = []
        self.max_delivery_history = 10000
        self._delivery_task: Optional[asyncio.Task] = None
        self._is_running = False
        self.listeners: List[Callable] = []

    async def register_webhook(
        self,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """Register a webhook."""
        webhook_id = str(uuid4())

        webhook = Webhook(
            webhook_id=webhook_id,
            url=url,
            events=events,
            secret=secret or self._generate_secret(),
            headers=headers or {},
        )

        self.webhooks[webhook_id] = webhook
        logger.info(f"Webhook registered: {webhook_id} for {len(events)} events")

        return webhook_id

    async def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[WebhookEvent]] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Update webhook configuration."""
        if webhook_id not in self.webhooks:
            return False

        webhook = self.webhooks[webhook_id]

        if url:
            webhook.url = url
        if events:
            webhook.events = events
        if is_active is not None:
            webhook.is_active = is_active

        webhook.updated_at = datetime.utcnow()
        logger.info(f"Webhook updated: {webhook_id}")

        return True

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id not in self.webhooks:
            return False

        del self.webhooks[webhook_id]
        logger.info(f"Webhook deleted: {webhook_id}")

        return True

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook by ID."""
        return self.webhooks.get(webhook_id)

    def list_webhooks(self, event_type: Optional[WebhookEvent] = None) -> List[Dict]:
        """List all webhooks, optionally filtered by event type."""
        webhooks = list(self.webhooks.values())

        if event_type:
            webhooks = [w for w in webhooks if event_type in w.events]

        return [
            {
                "webhook_id": w.webhook_id,
                "url": w.url,
                "events": [e.value for e in w.events],
                "is_active": w.is_active,
                "success_count": w.success_count,
                "failure_count": w.failure_count,
                "last_triggered": w.last_triggered.isoformat() if w.last_triggered else None,
            }
            for w in webhooks
        ]

    async def trigger_event(
        self,
        event_type: WebhookEvent,
        payload: Dict[str, Any],
    ) -> List[str]:
        """Trigger webhook event."""
        delivery_ids = []

        # Find all webhooks for this event
        for webhook in self.webhooks.values():
            if not webhook.is_active:
                continue

            if event_type not in webhook.events:
                continue

            # Create delivery
            delivery = WebhookDelivery(
                webhook_id=webhook.webhook_id,
                event_type=event_type,
                payload=payload,
                max_attempts=webhook.max_retries,
            )

            delivery_ids.append(delivery.delivery_id)
            await self._queue_delivery(delivery)

        logger.debug(f"Triggered {len(delivery_ids)} webhook deliveries for {event_type.value}")
        return delivery_ids

    async def _queue_delivery(self, delivery: WebhookDelivery) -> None:
        """Queue delivery for processing."""
        self.retry_queue.append(delivery)

    async def start(self) -> None:
        """Start webhook delivery worker."""
        if self._is_running:
            return

        self._is_running = True
        self._delivery_task = asyncio.create_task(self._delivery_worker())
        logger.info("Webhook manager started")

    async def stop(self) -> None:
        """Stop webhook delivery worker."""
        if not self._is_running:
            return

        self._is_running = False
        if self._delivery_task:
            self._delivery_task.cancel()
            try:
                await self._delivery_task
            except asyncio.CancelledError:
                pass

        logger.info("Webhook manager stopped")

    async def _delivery_worker(self) -> None:
        """Worker for processing webhook deliveries."""
        while self._is_running:
            try:
                while self.retry_queue and self._is_running:
                    delivery = self.retry_queue.pop(0)

                    success = await self._send_webhook(delivery)

                    if success:
                        delivery.success = True
                        delivery.completed_at = datetime.utcnow()
                        webhook = self.webhooks.get(delivery.webhook_id)
                        if webhook:
                            webhook.success_count += 1
                            webhook.last_triggered = datetime.utcnow()
                    else:
                        delivery.attempt += 1

                        if delivery.attempt <= delivery.max_attempts:
                            # Exponential backoff
                            retry_delay = min(2 ** (delivery.attempt - 1) * 5, 300)
                            delivery.next_retry = datetime.utcnow() + timedelta(
                                seconds=retry_delay
                            )
                            self.retry_queue.append(delivery)

                            webhook = self.webhooks.get(delivery.webhook_id)
                            if webhook:
                                webhook.failure_count += 1
                        else:
                            # Max retries exceeded
                            delivery.completed_at = datetime.utcnow()
                            webhook = self.webhooks.get(delivery.webhook_id)
                            if webhook:
                                webhook.failure_count += 1

                    self._store_delivery(delivery)

                    # Notify listeners
                    for listener in self.listeners:
                        try:
                            if asyncio.iscoroutinefunction(listener):
                                await listener(delivery)
                            else:
                                listener(delivery)
                        except Exception as e:
                            logger.error(f"Error in webhook listener: {e}")

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in delivery worker: {e}")
                await asyncio.sleep(5)

    async def _send_webhook(self, delivery: WebhookDelivery) -> bool:
        """Send webhook delivery."""
        webhook = self.webhooks.get(delivery.webhook_id)
        if not webhook:
            return False

        try:
            import aiohttp

            headers = {
                "Content-Type": "application/json",
                **webhook.headers,
            }

            # Add signature if secret exists
            if webhook.secret:
                payload_json = json.dumps(delivery.payload)
                signature = self._generate_signature(webhook.secret, payload_json)
                headers["X-Webhook-Signature"] = signature

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    json=delivery.payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=webhook.timeout_seconds),
                ) as response:
                    delivery.response_status = response.status
                    delivery.response_body = await response.text()

                    return response.status in [200, 201, 202, 204]

        except asyncio.TimeoutError:
            delivery.response_status = 408
            delivery.response_body = "Request timeout"
            return False
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            delivery.response_body = str(e)
            return False

    def _store_delivery(self, delivery: WebhookDelivery) -> None:
        """Store delivery record."""
        self.deliveries.append(delivery)

        if len(self.deliveries) > self.max_delivery_history:
            self.deliveries = self.deliveries[-self.max_delivery_history :]

    def get_delivery_history(
        self,
        webhook_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Get webhook delivery history."""
        deliveries = self.deliveries

        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]

        return [d.to_dict() for d in deliveries[-limit:]]

    def get_webhook_stats(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a webhook."""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return None

        deliveries = [d for d in self.deliveries if d.webhook_id == webhook_id]
        successful = sum(1 for d in deliveries if d.success)
        failed = len(deliveries) - successful

        return {
            "webhook_id": webhook_id,
            "total_deliveries": len(deliveries),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(deliveries) * 100) if deliveries else 0,
            "last_triggered": webhook.last_triggered.isoformat()
            if webhook.last_triggered
            else None,
        }

    async def subscribe(self, callback: Callable) -> None:
        """Subscribe to webhook delivery events."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    async def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from webhook delivery events."""
        if callback in self.listeners:
            self.listeners.remove(callback)

    @staticmethod
    def _generate_secret() -> str:
        """Generate webhook secret."""
        import secrets

        return secrets.token_urlsafe(32)

    @staticmethod
    def _generate_signature(secret: str, payload: str) -> str:
        """Generate HMAC signature for webhook."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()


# Global webhook manager instance
_webhook_manager: Optional[WebhookManager] = None


async def get_webhook_manager() -> WebhookManager:
    """Get or create global webhook manager."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
        await _webhook_manager.start()
    return _webhook_manager
