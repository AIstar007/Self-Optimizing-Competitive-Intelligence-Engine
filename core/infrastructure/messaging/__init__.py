"""
Messaging module initialization with broker and router exports.
"""

from .broker import (
    Message,
    MessageBroker,
    BrokerConfig,
    MessageBrokerType,
    MessagePriority,
    MessageStatus,
    MessageStats,
    RabbitMQBroker,
    InMemoryBroker,
    get_message_broker,
)
from .router import (
    MessageHandler,
    MessageRouter,
    RoutingRule,
    MessageHandlerStats,
    RouterMiddleware,
    ValidationMiddleware,
    LoggingMiddleware,
    RetryMiddleware,
    get_message_router,
)

__all__ = [
    "Message",
    "MessageBroker",
    "BrokerConfig",
    "MessageBrokerType",
    "MessagePriority",
    "MessageStatus",
    "MessageStats",
    "RabbitMQBroker",
    "InMemoryBroker",
    "get_message_broker",
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
