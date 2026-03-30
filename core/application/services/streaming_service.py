"""Real-time streaming service for KPI, metric, and alert updates."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class StreamType(str, Enum):
    """Types of data streams."""

    KPI = "kpi"
    METRIC = "metric"
    ALERT = "alert"
    TREND = "trend"
    FORECAST = "forecast"


@dataclass
class StreamEvent:
    """Represents a streaming event."""

    event_id: str
    stream_type: StreamType
    entity_id: str
    data: Dict[str, Any]
    timestamp: datetime
    priority: int = 0  # Higher = more important


class StreamBuffer:
    """Buffer for streaming events with priority queuing."""

    def __init__(self, max_size: int = 1000):
        """Initialize stream buffer."""
        self.max_size = max_size
        self.events: List[StreamEvent] = []
        self.lock = asyncio.Lock()

    async def add_event(self, event: StreamEvent) -> bool:
        """Add event to buffer."""
        async with self.lock:
            if len(self.events) >= self.max_size:
                # Remove lowest priority event
                self.events.sort(key=lambda e: e.priority)
                self.events.pop(0)

            self.events.append(event)
            self.events.sort(key=lambda e: -e.priority)
            return True

    async def get_event(self) -> Optional[StreamEvent]:
        """Get highest priority event from buffer."""
        async with self.lock:
            if not self.events:
                return None
            return self.events.pop(0)

    async def get_batch(self, batch_size: int) -> List[StreamEvent]:
        """Get batch of events from buffer."""
        async with self.lock:
            batch = self.events[:batch_size]
            self.events = self.events[batch_size:]
            return batch

    async def clear(self) -> int:
        """Clear all events and return count."""
        async with self.lock:
            count = len(self.events)
            self.events.clear()
            return count

    async def size(self) -> int:
        """Get current buffer size."""
        async with self.lock:
            return len(self.events)


class StreamingService:
    """Service for real-time data streaming to connected clients."""

    def __init__(self):
        """Initialize streaming service."""
        self.buffer = StreamBuffer()
        self.subscribers: Dict[str, List[Callable]] = {
            "kpi": [],
            "metric": [],
            "alert": [],
            "trend": [],
            "forecast": [],
        }
        self.event_history: Dict[str, List[StreamEvent]] = {}
        self.max_history_per_stream = 100
        self._processing_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        """Start streaming service."""
        if self._is_running:
            return

        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_stream())
        logger.info("Streaming service started")

    async def stop(self) -> None:
        """Stop streaming service."""
        if not self._is_running:
            return

        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        logger.info("Streaming service stopped")

    async def emit_kpi_update(
        self,
        kpi_id: str,
        company_id: str,
        kpi_data: Dict[str, Any],
        priority: int = 5,
    ) -> None:
        """Emit a KPI update to streaming service."""
        event = StreamEvent(
            event_id=f"kpi_{kpi_id}_{datetime.utcnow().timestamp()}",
            stream_type=StreamType.KPI,
            entity_id=kpi_id,
            data={
                "kpi_id": kpi_id,
                "company_id": company_id,
                "kpi_data": kpi_data,
            },
            timestamp=datetime.utcnow(),
            priority=priority,
        )

        await self.buffer.add_event(event)
        await self._notify_subscribers(StreamType.KPI, event)

    async def emit_metric_update(
        self,
        metric_id: str,
        metric_data: Dict[str, Any],
        priority: int = 4,
    ) -> None:
        """Emit a metric update to streaming service."""
        event = StreamEvent(
            event_id=f"metric_{metric_id}_{datetime.utcnow().timestamp()}",
            stream_type=StreamType.METRIC,
            entity_id=metric_id,
            data={
                "metric_id": metric_id,
                "metric_data": metric_data,
            },
            timestamp=datetime.utcnow(),
            priority=priority,
        )

        await self.buffer.add_event(event)
        await self._notify_subscribers(StreamType.METRIC, event)

    async def emit_alert(
        self,
        alert_id: str,
        alert_data: Dict[str, Any],
        priority: int = 8,
    ) -> None:
        """Emit an alert to streaming service."""
        event = StreamEvent(
            event_id=f"alert_{alert_id}_{datetime.utcnow().timestamp()}",
            stream_type=StreamType.ALERT,
            entity_id=alert_id,
            data={
                "alert_id": alert_id,
                "alert_data": alert_data,
            },
            timestamp=datetime.utcnow(),
            priority=priority,
        )

        await self.buffer.add_event(event)
        await self._notify_subscribers(StreamType.ALERT, event)

    async def emit_trend_update(
        self,
        company_id: str,
        metric_name: str,
        trend_data: Dict[str, Any],
        priority: int = 6,
    ) -> None:
        """Emit a trend update to streaming service."""
        event = StreamEvent(
            event_id=f"trend_{company_id}_{metric_name}_{datetime.utcnow().timestamp()}",
            stream_type=StreamType.TREND,
            entity_id=f"{company_id}_{metric_name}",
            data={
                "company_id": company_id,
                "metric_name": metric_name,
                "trend_data": trend_data,
            },
            timestamp=datetime.utcnow(),
            priority=priority,
        )

        await self.buffer.add_event(event)
        await self._notify_subscribers(StreamType.TREND, event)

    async def emit_forecast_update(
        self,
        company_id: str,
        kpi_name: str,
        forecast_data: Dict[str, Any],
        priority: int = 5,
    ) -> None:
        """Emit a forecast update to streaming service."""
        event = StreamEvent(
            event_id=f"forecast_{company_id}_{kpi_name}_{datetime.utcnow().timestamp()}",
            stream_type=StreamType.FORECAST,
            entity_id=f"{company_id}_{kpi_name}",
            data={
                "company_id": company_id,
                "kpi_name": kpi_name,
                "forecast_data": forecast_data,
            },
            timestamp=datetime.utcnow(),
            priority=priority,
        )

        await self.buffer.add_event(event)
        await self._notify_subscribers(StreamType.FORECAST, event)

    async def subscribe(
        self,
        stream_type: StreamType,
        callback: Callable,
    ) -> None:
        """Subscribe to stream events."""
        key = stream_type.value
        if callback not in self.subscribers[key]:
            self.subscribers[key].append(callback)
            logger.debug(f"New subscriber for {stream_type.value} stream")

    async def unsubscribe(
        self,
        stream_type: StreamType,
        callback: Callable,
    ) -> None:
        """Unsubscribe from stream events."""
        key = stream_type.value
        if callback in self.subscribers[key]:
            self.subscribers[key].remove(callback)
            logger.debug(f"Removed subscriber for {stream_type.value} stream")

    async def _notify_subscribers(
        self,
        stream_type: StreamType,
        event: StreamEvent,
    ) -> None:
        """Notify all subscribers of an event."""
        key = stream_type.value
        for callback in self.subscribers[key]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

        # Store in history
        if key not in self.event_history:
            self.event_history[key] = []

        history = self.event_history[key]
        history.append(event)

        if len(history) > self.max_history_per_stream:
            history.pop(0)

    async def _process_stream(self) -> None:
        """Process streaming events from buffer."""
        while self._is_running:
            try:
                # Get batch of events
                events = await self.buffer.get_batch(batch_size=10)

                for event in events:
                    await self._notify_subscribers(event.stream_type, event)

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing stream: {e}")
                await asyncio.sleep(1)

    async def get_event_history(
        self,
        stream_type: StreamType,
        limit: int = 50,
    ) -> List[StreamEvent]:
        """Get recent event history for a stream type."""
        key = stream_type.value
        history = self.event_history.get(key, [])
        return history[-limit:] if limit else history

    async def get_statistics(self) -> Dict[str, Any]:
        """Get streaming service statistics."""
        return {
            "is_running": self._is_running,
            "buffer_size": await self.buffer.size(),
            "subscribers_count": sum(len(subs) for subs in self.subscribers.values()),
            "subscribers_by_type": {k: len(v) for k, v in self.subscribers.items()},
            "history_size": {k: len(v) for k, v in self.event_history.items()},
        }

    async def flush_buffer(self) -> int:
        """Flush all pending events from buffer."""
        return await self.buffer.clear()


# Global streaming service instance
_streaming_service: Optional[StreamingService] = None


async def get_streaming_service() -> StreamingService:
    """Get or create global streaming service."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
        await _streaming_service.start()
    return _streaming_service
