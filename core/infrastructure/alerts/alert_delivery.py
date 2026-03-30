"""Alert delivery mechanisms (email, Slack, webhooks, etc.)."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertDeliveryStatus(str, Enum):
    """Alert delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"


class EmailDeliveryConfig:
    """Email delivery configuration."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
    ):
        """Initialize email config."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password


class SlackDeliveryConfig:
    """Slack delivery configuration."""

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        """Initialize Slack config."""
        self.webhook_url = webhook_url
        self.channel = channel


class WebhookDeliveryConfig:
    """Webhook delivery configuration."""

    def __init__(self, endpoint_url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize webhook config."""
        self.endpoint_url = endpoint_url
        self.headers = headers or {}


class AlertDeliveryRecord:
    """Record of alert delivery attempt."""

    def __init__(
        self,
        alert_id: str,
        channel: str,
        recipient: str,
        status: AlertDeliveryStatus,
        timestamp: datetime = None,
        error_message: Optional[str] = None,
    ):
        """Initialize delivery record."""
        self.alert_id = alert_id
        self.channel = channel
        self.recipient = recipient
        self.status = status
        self.timestamp = timestamp or datetime.utcnow()
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "channel": self.channel,
            "recipient": self.recipient,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }


class AlertDeliveryProvider:
    """Base class for alert delivery providers."""

    async def send(self, alert_data: Dict[str, Any], recipient: str) -> bool:
        """Send alert to recipient."""
        raise NotImplementedError


class EmailDeliveryProvider(AlertDeliveryProvider):
    """Email alert delivery provider."""

    def __init__(self, config: EmailDeliveryConfig):
        """Initialize email provider."""
        self.config = config

    async def send(self, alert_data: Dict[str, Any], recipient: str) -> bool:
        """Send alert via email."""
        try:
            # In production, use aiosmtplib for async email
            logger.info(f"Sending email alert to {recipient}")
            # Placeholder for actual email sending
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


class SlackDeliveryProvider(AlertDeliveryProvider):
    """Slack alert delivery provider."""

    def __init__(self, config: SlackDeliveryConfig):
        """Initialize Slack provider."""
        self.config = config

    async def send(self, alert_data: Dict[str, Any], recipient: str) -> bool:
        """Send alert via Slack."""
        try:
            # Format message for Slack
            message = self._format_slack_message(alert_data)

            # In production, use aiohttp for async requests
            logger.info(f"Sending Slack alert to {recipient}")
            # Placeholder for actual Slack sending
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _format_slack_message(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert as Slack message."""
        severity = alert_data.get("severity", "info").upper()

        color_map = {
            "INFO": "#36A64F",
            "WARNING": "#FFA500",
            "CRITICAL": "#FF0000",
        }

        return {
            "channel": self.config.channel,
            "attachments": [
                {
                    "fallback": alert_data.get("title", "Alert"),
                    "color": color_map.get(severity, "#36A64F"),
                    "title": alert_data.get("title", "Alert"),
                    "text": alert_data.get("message", ""),
                    "fields": [
                        {
                            "title": "Severity",
                            "value": severity,
                            "short": True,
                        },
                        {
                            "title": "Source",
                            "value": alert_data.get("source", "Unknown"),
                            "short": True,
                        },
                        {
                            "title": "Company",
                            "value": alert_data.get("company_id", "Unknown"),
                            "short": True,
                        },
                        {
                            "title": "Time",
                            "value": alert_data.get("created_at", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        }


class WebhookDeliveryProvider(AlertDeliveryProvider):
    """Webhook alert delivery provider."""

    def __init__(self, config: WebhookDeliveryConfig):
        """Initialize webhook provider."""
        self.config = config

    async def send(self, alert_data: Dict[str, Any], recipient: str) -> bool:
        """Send alert via webhook."""
        try:
            # In production, use aiohttp for async requests
            payload = json.dumps(alert_data)
            logger.info(f"Sending webhook alert to {recipient}")
            # Placeholder for actual webhook sending
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class AlertDeliveryManager:
    """Manages alert delivery across multiple channels."""

    def __init__(self):
        """Initialize delivery manager."""
        self.providers: Dict[str, AlertDeliveryProvider] = {}
        self.delivery_records: List[AlertDeliveryRecord] = []
        self.max_records = 10000
        self.retry_queue: List[tuple] = []
        self._retry_task: Optional[asyncio.Task] = None
        self._is_running = False

    def register_provider(self, channel: str, provider: AlertDeliveryProvider) -> None:
        """Register delivery provider."""
        self.providers[channel] = provider
        logger.info(f"Registered delivery provider for channel: {channel}")

    async def send_alert(
        self,
        alert_data: Dict[str, Any],
        channels: List[str],
        recipients: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Send alert through multiple channels."""
        results = {}

        for channel in channels:
            if channel not in self.providers:
                logger.warning(f"No provider for channel: {channel}")
                results[channel] = {"status": "failed", "reason": "No provider"}
                continue

            provider = self.providers[channel]
            channel_recipients = recipients.get(channel, []) if recipients else []

            if not channel_recipients:
                logger.debug(f"No recipients for channel: {channel}")
                continue

            for recipient in channel_recipients:
                success = await provider.send(alert_data, recipient)

                record = AlertDeliveryRecord(
                    alert_id=alert_data.get("alert_id"),
                    channel=channel,
                    recipient=recipient,
                    status=AlertDeliveryStatus.SENT if success else AlertDeliveryStatus.FAILED,
                    error_message=None if success else "Delivery failed",
                )

                self._store_record(record)
                results.setdefault(channel, []).append(record.to_dict())

                if not success:
                    await self._queue_retry(alert_data, channel, recipient)

        return results

    async def _queue_retry(
        self,
        alert_data: Dict[str, Any],
        channel: str,
        recipient: str,
        retry_count: int = 0,
    ) -> None:
        """Queue alert for retry."""
        if retry_count < 3:
            self.retry_queue.append((alert_data, channel, recipient, retry_count + 1))
            logger.debug(f"Queued retry for {channel} to {recipient}")

    async def start_retry_worker(self) -> None:
        """Start worker for retrying failed deliveries."""
        if self._is_running:
            return

        self._is_running = True
        self._retry_task = asyncio.create_task(self._retry_worker())
        logger.info("Alert retry worker started")

    async def stop_retry_worker(self) -> None:
        """Stop retry worker."""
        if not self._is_running:
            return

        self._is_running = False
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert retry worker stopped")

    async def _retry_worker(self) -> None:
        """Worker for retrying failed alerts."""
        while self._is_running:
            try:
                while self.retry_queue and self._is_running:
                    alert_data, channel, recipient, retry_count = self.retry_queue.pop(0)

                    if channel in self.providers:
                        provider = self.providers[channel]
                        success = await provider.send(alert_data, recipient)

                        record = AlertDeliveryRecord(
                            alert_id=alert_data.get("alert_id"),
                            channel=channel,
                            recipient=recipient,
                            status=AlertDeliveryStatus.DELIVERED
                            if success
                            else AlertDeliveryStatus.FAILED,
                            error_message=None if success else "Retry failed",
                        )

                        self._store_record(record)

                        if not success and retry_count < 3:
                            await self._queue_retry(alert_data, channel, recipient, retry_count)

                        logger.info(
                            f"Retried alert {alert_data.get('alert_id')} "
                            f"({retry_count}): {channel} to {recipient}"
                        )

                    # Delay between retries
                    await asyncio.sleep(5)

                # Wait before checking again
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry worker: {e}")
                await asyncio.sleep(5)

    def _store_record(self, record: AlertDeliveryRecord) -> None:
        """Store delivery record."""
        self.delivery_records.append(record)

        if len(self.delivery_records) > self.max_records:
            # Remove oldest records
            self.delivery_records = self.delivery_records[-self.max_records :]

    async def get_delivery_status(self, alert_id: str) -> List[Dict[str, Any]]:
        """Get delivery status for alert."""
        records = [r for r in self.delivery_records if r.alert_id == alert_id]
        return [r.to_dict() for r in records]

    async def get_statistics(self) -> Dict[str, Any]:
        """Get delivery statistics."""
        total = len(self.delivery_records)

        if total == 0:
            return {
                "total_deliveries": 0,
                "successful": 0,
                "failed": 0,
                "pending_retries": len(self.retry_queue),
            }

        successful = sum(
            1
            for r in self.delivery_records
            if r.status in [AlertDeliveryStatus.DELIVERED, AlertDeliveryStatus.SENT]
        )
        failed = sum(1 for r in self.delivery_records if r.status == AlertDeliveryStatus.FAILED)

        return {
            "total_deliveries": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "pending_retries": len(self.retry_queue),
            "channels": list(self.providers.keys()),
        }


# Global delivery manager instance
_delivery_manager: Optional[AlertDeliveryManager] = None


def get_alert_delivery_manager() -> AlertDeliveryManager:
    """Get or create global delivery manager."""
    global _delivery_manager
    if _delivery_manager is None:
        _delivery_manager = AlertDeliveryManager()
    return _delivery_manager
