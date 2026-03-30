"""
Message Routing and Handler Module
Routes messages to appropriate handlers based on routing keys and patterns.
Implements message handler registry and middleware.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Set
from collections import defaultdict
from datetime import datetime

from .broker import Message, MessageStatus

logger = logging.getLogger(__name__)


class MessageHandler(ABC):
    """Abstract base class for message handlers."""
    
    @abstractmethod
    async def can_handle(self, message: Message) -> bool:
        """Check if handler can process message."""
        pass
    
    @abstractmethod
    async def handle(self, message: Message) -> bool:
        """Process message. Returns True if successful."""
        pass


@dataclass
class RoutingRule:
    """Message routing rule."""
    pattern: str
    handler: MessageHandler
    priority: int = 0
    enabled: bool = True
    regex: Optional[Pattern] = field(default=None, init=False)
    
    def __post_init__(self):
        """Compile routing pattern."""
        self.regex = re.compile(self.pattern)
    
    def matches(self, routing_key: str) -> bool:
        """Check if routing key matches pattern."""
        return bool(self.regex.match(routing_key)) if self.regex else False


@dataclass
class MessageHandlerStats:
    """Handler statistics."""
    routing_key: str = ""
    total_handled: int = 0
    total_successful: int = 0
    total_failed: int = 0
    avg_processing_time: float = 0.0
    last_processed: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None


class RouterMiddleware(ABC):
    """Abstract base for router middleware."""
    
    @abstractmethod
    async def before_route(self, message: Message) -> bool:
        """Execute before message routing. Return False to skip routing."""
        pass
    
    @abstractmethod
    async def after_route(self, message: Message, success: bool) -> None:
        """Execute after message routing."""
        pass


class ValidationMiddleware(RouterMiddleware):
    """Validates message structure and content."""
    
    async def before_route(self, message: Message) -> bool:
        """Validate message."""
        if not message.body:
            logger.warning(f"Empty message body for {message.id}")
            return False
        
        if not message.routing_key:
            logger.warning(f"Missing routing key for message {message.id}")
            return False
        
        return True
    
    async def after_route(self, message: Message, success: bool) -> None:
        """Log validation results."""
        if not success:
            logger.debug(f"Message {message.id} validation failed")


class LoggingMiddleware(RouterMiddleware):
    """Logs message routing events."""
    
    async def before_route(self, message: Message) -> bool:
        """Log incoming message."""
        logger.debug(f"Routing message {message.id} with key {message.routing_key}")
        return True
    
    async def after_route(self, message: Message, success: bool) -> None:
        """Log routing result."""
        status = "successful" if success else "failed"
        logger.debug(f"Message {message.id} routing {status}")


class RetryMiddleware(RouterMiddleware):
    """Handles message retry logic."""
    
    def __init__(self, max_retries: int = 3):
        """Initialize retry middleware."""
        self.max_retries = max_retries
    
    async def before_route(self, message: Message) -> bool:
        """Check retry status."""
        if message.retries > self.max_retries:
            logger.error(
                f"Message {message.id} exceeded max retries "
                f"({message.retries}/{self.max_retries})"
            )
            message.status = MessageStatus.DEAD_LETTERED
            return False
        return True
    
    async def after_route(self, message: Message, success: bool) -> None:
        """Update retry count on failure."""
        if not success:
            message.retries += 1
            logger.debug(f"Message {message.id} retry count: {message.retries}")


class MessageRouter:
    """Routes messages to appropriate handlers based on routing keys."""
    
    def __init__(self, default_handler: Optional[MessageHandler] = None):
        """Initialize message router."""
        self._rules: List[RoutingRule] = []
        self._default_handler = default_handler
        self._middlewares: List[RouterMiddleware] = []
        self._stats: Dict[str, MessageHandlerStats] = defaultdict(
            lambda: MessageHandlerStats()
        )
        self._handler_cache: Dict[str, List[RoutingRule]] = {}
        self._lock = asyncio.Lock()
    
    def add_rule(
        self,
        pattern: str,
        handler: MessageHandler,
        priority: int = 0
    ) -> None:
        """Add message routing rule."""
        rule = RoutingRule(pattern=pattern, handler=handler, priority=priority)
        self._rules.append(rule)
        # Sort by priority descending
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self._handler_cache.clear()
        logger.info(f"Added routing rule: {pattern} -> priority {priority}")
    
    def remove_rule(self, pattern: str) -> bool:
        """Remove routing rule by pattern."""
        original_length = len(self._rules)
        self._rules = [r for r in self._rules if r.pattern != pattern]
        removed = len(self._rules) < original_length
        if removed:
            self._handler_cache.clear()
        return removed
    
    def add_middleware(self, middleware: RouterMiddleware) -> None:
        """Add router middleware."""
        self._middlewares.append(middleware)
        logger.debug(f"Added middleware: {middleware.__class__.__name__}")
    
    def remove_middleware(self, middleware: RouterMiddleware) -> None:
        """Remove router middleware."""
        self._middlewares.remove(middleware)
    
    async def route(self, message: Message) -> bool:
        """Route message to appropriate handler."""
        async with self._lock:
            # Run before_route middleware
            for middleware in self._middlewares:
                if not await middleware.before_route(message):
                    await self._update_stats(message, False)
                    return False
            
            # Find matching handlers
            handlers = self._find_handlers(message.routing_key)
            
            if not handlers and self._default_handler:
                handlers = [self._default_handler]
            
            if not handlers:
                logger.warning(
                    f"No handlers found for routing key: {message.routing_key}"
                )
                message.status = MessageStatus.FAILED
                await self._update_stats(message, False)
                return False
            
            # Execute handlers
            success = False
            for handler in handlers:
                try:
                    if await handler.can_handle(message):
                        success = await handler.handle(message)
                        if success:
                            message.status = MessageStatus.PROCESSED
                            break
                except Exception as e:
                    logger.error(f"Handler error for message {message.id}: {e}")
                    message.error = str(e)
                    message.status = MessageStatus.FAILED
            
            # Run after_route middleware
            for middleware in self._middlewares:
                await middleware.after_route(message, success)
            
            await self._update_stats(message, success)
            return success
    
    def _find_handlers(self, routing_key: str) -> List[MessageHandler]:
        """Find handlers for routing key (with caching)."""
        if routing_key in self._handler_cache:
            return [r.handler for r in self._handler_cache[routing_key]]
        
        matching_rules = [
            rule for rule in self._rules
            if rule.enabled and rule.matches(routing_key)
        ]
        
        self._handler_cache[routing_key] = matching_rules
        return [rule.handler for rule in matching_rules]
    
    async def _update_stats(self, message: Message, success: bool) -> None:
        """Update routing statistics."""
        stats = self._stats[message.routing_key]
        stats.routing_key = message.routing_key
        stats.total_handled += 1
        stats.last_processed = datetime.utcnow()
        
        if success:
            stats.total_successful += 1
        else:
            stats.total_failed += 1
            stats.error_count += 1
            stats.last_error = message.error
    
    def get_stats(self) -> Dict[str, MessageHandlerStats]:
        """Get routing statistics."""
        return dict(self._stats)
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get configured routing rules."""
        return [
            {
                'pattern': rule.pattern,
                'priority': rule.priority,
                'enabled': rule.enabled,
                'handler': rule.handler.__class__.__name__
            }
            for rule in self._rules
        ]


# Singleton instance
_router_instance: Optional[MessageRouter] = None
_router_lock = asyncio.Lock()


async def get_message_router(
    default_handler: Optional[MessageHandler] = None
) -> MessageRouter:
    """Get or create message router singleton."""
    global _router_instance
    
    if _router_instance is None:
        async with _router_lock:
            if _router_instance is None:
                _router_instance = MessageRouter(default_handler)
                # Add default middleware
                _router_instance.add_middleware(ValidationMiddleware())
                _router_instance.add_middleware(LoggingMiddleware())
                _router_instance.add_middleware(RetryMiddleware())
    
    return _router_instance


__all__ = [
    "MessageHandler",
    "MessageRouter",
    "RoutingRule",
    "MessageHandlerStats",
    "RouterMiddleware",
    "ValidationMiddleware",
    "LoggingMiddleware",
    "RetryMiddleware",
    "get_message_router",
]
