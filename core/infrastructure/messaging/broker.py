"""
Message Broker Integration Module
Supports RabbitMQ and Kafka for distributed messaging patterns.
Provides abstraction layer for message publishing and consumption.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Thread, Lock
from collections import defaultdict, deque
import pika
from pika.adapters.blocking_connection import BlockingConnection
import pika.exceptions as pika_exceptions

logger = logging.getLogger(__name__)


class MessageBrokerType(Enum):
    """Supported message broker types."""
    RABBITMQ = "rabbitmq"
    KAFKA = "kafka"
    IN_MEMORY = "in_memory"


class MessagePriority(Enum):
    """Message priority levels for queue ordering."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


@dataclass
class Message:
    """Message data structure with metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    exchange: str = ""
    routing_key: str = ""
    body: Dict[str, Any] = field(default_factory=dict)
    content_type: str = "application/json"
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    retries: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.name
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert message to JSON."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class BrokerConfig:
    """Message broker configuration."""
    broker_type: MessageBrokerType = MessageBrokerType.RABBITMQ
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    max_connections: int = 10
    heartbeat: int = 600
    prefetch_count: int = 1
    connection_timeout: int = 10
    queue_ttl: int = 86400  # 24 hours
    message_ttl: int = 3600  # 1 hour
    enable_durable_queues: bool = True
    enable_ack: bool = True
    dead_letter_exchange: str = "dlx"
    dead_letter_ttl: int = 604800  # 7 days


@dataclass
class MessageStats:
    """Message statistics tracker."""
    total_published: int = 0
    total_consumed: int = 0
    total_failed: int = 0
    total_acknowledged: int = 0
    avg_processing_time: float = 0.0
    messages_in_queue: int = 0
    max_queue_size: int = 0
    consumers_active: int = 0
    publishers_active: int = 0


class MessageBroker(ABC):
    """Abstract base class for message brokers."""
    
    def __init__(self, config: BrokerConfig):
        """Initialize message broker."""
        self.config = config
        self.stats = MessageStats()
        self._lock = Lock()
        self._connection = None
        self._channel = None
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to message broker."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to message broker."""
        pass
    
    @abstractmethod
    async def publish(self, message: Message) -> bool:
        """Publish message to broker."""
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        queue_name: str,
        callback: Callable[[Message], Any],
        auto_ack: bool = True
    ) -> str:
        """Subscribe to message queue."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from message queue."""
        pass
    
    @abstractmethod
    async def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False
    ) -> None:
        """Declare queue on broker."""
        pass
    
    @abstractmethod
    async def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: str = "topic",
        durable: bool = True
    ) -> None:
        """Declare exchange on broker."""
        pass
    
    @abstractmethod
    async def bind_queue(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str
    ) -> None:
        """Bind queue to exchange with routing key."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> MessageStats:
        """Get message broker statistics."""
        pass
    
    @abstractmethod
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from queue."""
        pass


class RabbitMQBroker(MessageBroker):
    """RabbitMQ message broker implementation."""
    
    def __init__(self, config: BrokerConfig):
        """Initialize RabbitMQ broker."""
        super().__init__(config)
        self._subscriptions: Dict[str, Callable] = {}
        self._consumer_threads: Dict[str, Thread] = {}
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(
                self.config.username,
                self.config.password
            )
            parameters = pika.ConnectionParameters(
                host=self.config.host,
                port=self.config.port,
                virtual_host=self.config.virtual_host,
                credentials=credentials,
                heartbeat=self.config.heartbeat,
                connection_attempts=3,
                retry_delay=2,
                socket_timeout=self.config.connection_timeout
            )
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            self._channel.basic_qos(prefetch_count=self.config.prefetch_count)
            
            logger.info(f"Connected to RabbitMQ at {self.config.host}:{self.config.port}")
        except pika_exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def publish(self, message: Message) -> bool:
        """Publish message to RabbitMQ."""
        if not self._channel:
            logger.error("Channel not established")
            return False
        
        try:
            properties = pika.BasicProperties(
                content_type=message.content_type,
                delivery_mode=2 if self.config.enable_durable_queues else 1,
                priority=message.priority.value,
                correlation_id=message.correlation_id or message.id,
                reply_to=message.reply_to,
                headers=message.headers,
                expiration=str(self.config.message_ttl * 1000)
            )
            
            self._channel.basic_publish(
                exchange=message.exchange,
                routing_key=message.routing_key,
                body=message.to_json(),
                properties=properties
            )
            
            with self._lock:
                self.stats.total_published += 1
                message.status = MessageStatus.SENT
            
            logger.debug(f"Published message {message.id} to {message.routing_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message {message.id}: {e}")
            with self._lock:
                self.stats.total_failed += 1
                message.status = MessageStatus.FAILED
                message.error = str(e)
            return False
    
    async def subscribe(
        self,
        queue_name: str,
        callback: Callable[[Message], Any],
        auto_ack: bool = True
    ) -> str:
        """Subscribe to message queue."""
        subscription_id = str(uuid.uuid4())
        self._subscriptions[subscription_id] = callback
        
        def consumer_callback(ch, method, properties, body):
            try:
                data = json.loads(body.decode())
                message = Message(
                    id=properties.correlation_id or str(uuid.uuid4()),
                    exchange=method.exchange,
                    routing_key=method.routing_key,
                    body=data,
                    headers=properties.headers or {},
                    correlation_id=properties.correlation_id,
                    reply_to=properties.reply_to
                )
                
                callback(message)
                message.status = MessageStatus.PROCESSED
                
                with self._lock:
                    self.stats.total_consumed += 1
                    self.stats.total_acknowledged += 1
                
                if self.config.enable_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing message in {queue_name}: {e}")
                with self._lock:
                    self.stats.total_failed += 1
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        self._channel.basic_consume(
            queue=queue_name,
            on_message_callback=consumer_callback,
            auto_ack=False
        )
        
        logger.info(f"Subscribed to {queue_name} with subscription {subscription_id}")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from message queue."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info(f"Unsubscribed from {subscription_id}")
    
    async def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False
    ) -> None:
        """Declare queue on RabbitMQ."""
        if not self._channel:
            raise RuntimeError("Channel not established")
        
        arguments = {}
        if self.config.queue_ttl:
            arguments['x-message-ttl'] = self.config.queue_ttl * 1000
        if self.config.dead_letter_exchange:
            arguments['x-dead-letter-exchange'] = self.config.dead_letter_exchange
        
        self._channel.queue_declare(
            queue=queue_name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=arguments or None
        )
        logger.debug(f"Declared queue {queue_name}")
    
    async def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: str = "topic",
        durable: bool = True
    ) -> None:
        """Declare exchange on RabbitMQ."""
        if not self._channel:
            raise RuntimeError("Channel not established")
        
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=durable
        )
        logger.debug(f"Declared exchange {exchange_name}")
    
    async def bind_queue(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str
    ) -> None:
        """Bind queue to exchange with routing key."""
        if not self._channel:
            raise RuntimeError("Channel not established")
        
        self._channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )
        logger.debug(f"Bound queue {queue_name} to {exchange_name}:{routing_key}")
    
    async def get_stats(self) -> MessageStats:
        """Get message broker statistics."""
        with self._lock:
            return MessageStats(
                total_published=self.stats.total_published,
                total_consumed=self.stats.total_consumed,
                total_failed=self.stats.total_failed,
                total_acknowledged=self.stats.total_acknowledged,
                consumers_active=len(self._subscriptions),
                publishers_active=1
            )
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from queue."""
        if not self._channel:
            raise RuntimeError("Channel not established")
        
        result = self._channel.queue_purge(queue=queue_name)
        logger.info(f"Purged {result.method.message_count} messages from {queue_name}")
        return result.method.message_count


class InMemoryBroker(MessageBroker):
    """In-memory message broker for testing."""
    
    def __init__(self, config: BrokerConfig):
        """Initialize in-memory broker."""
        super().__init__(config)
        self._queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        self._exchanges: Dict[str, str] = {}
        self._bindings: Dict[str, List[str]] = defaultdict(list)
    
    async def connect(self) -> None:
        """Connect in-memory broker (no-op)."""
        logger.info("In-memory broker connected")
    
    async def disconnect(self) -> None:
        """Disconnect in-memory broker (no-op)."""
        logger.info("In-memory broker disconnected")
    
    async def publish(self, message: Message) -> bool:
        """Publish message to in-memory queue."""
        try:
            queues = self._bindings.get(f"{message.exchange}:{message.routing_key}", [])
            for queue_name in queues:
                self._queues[queue_name].append(message)
            
            with self._lock:
                self.stats.total_published += 1
                self.stats.messages_in_queue = sum(len(q) for q in self._queues.values())
                self.stats.max_queue_size = max(
                    self.stats.max_queue_size,
                    self.stats.messages_in_queue
                )
                message.status = MessageStatus.SENT
            
            logger.debug(f"In-memory published message {message.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish in-memory message: {e}")
            with self._lock:
                self.stats.total_failed += 1
            return False
    
    async def subscribe(
        self,
        queue_name: str,
        callback: Callable[[Message], Any],
        auto_ack: bool = True
    ) -> str:
        """Subscribe to in-memory queue."""
        subscription_id = str(uuid.uuid4())
        self._subscribers[queue_name].add(callback)
        
        async def consume():
            while subscription_id in self._subscribers.get(queue_name, set()):
                if self._queues[queue_name]:
                    message = self._queues[queue_name].popleft()
                    try:
                        callback(message)
                        message.status = MessageStatus.PROCESSED
                        with self._lock:
                            self.stats.total_consumed += 1
                            self.stats.total_acknowledged += 1
                    except Exception as e:
                        logger.error(f"Error in in-memory callback: {e}")
                        with self._lock:
                            self.stats.total_failed += 1
                await asyncio.sleep(0.1)
        
        asyncio.create_task(consume())
        logger.info(f"Subscribed to in-memory queue {queue_name}")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from in-memory queue."""
        for queue_subscribers in self._subscribers.values():
            queue_subscribers.discard(subscription_id)
    
    async def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False
    ) -> None:
        """Declare in-memory queue."""
        self._queues[queue_name] = deque(maxlen=1000)
        logger.debug(f"In-memory queue {queue_name} declared")
    
    async def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: str = "topic",
        durable: bool = True
    ) -> None:
        """Declare in-memory exchange."""
        self._exchanges[exchange_name] = exchange_type
        logger.debug(f"In-memory exchange {exchange_name} declared")
    
    async def bind_queue(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str
    ) -> None:
        """Bind in-memory queue to exchange."""
        binding_key = f"{exchange_name}:{routing_key}"
        self._bindings[binding_key].append(queue_name)
        logger.debug(f"In-memory binding {binding_key} -> {queue_name}")
    
    async def get_stats(self) -> MessageStats:
        """Get in-memory broker statistics."""
        with self._lock:
            return MessageStats(
                total_published=self.stats.total_published,
                total_consumed=self.stats.total_consumed,
                total_failed=self.stats.total_failed,
                total_acknowledged=self.stats.total_acknowledged,
                messages_in_queue=sum(len(q) for q in self._queues.values()),
                max_queue_size=self.stats.max_queue_size,
                consumers_active=len(self._subscribers)
            )
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from in-memory queue."""
        count = len(self._queues[queue_name])
        self._queues[queue_name].clear()
        logger.info(f"Purged {count} messages from in-memory queue {queue_name}")
        return count


_broker_instance: Optional[MessageBroker] = None
_broker_lock = Lock()


def get_message_broker(config: Optional[BrokerConfig] = None) -> MessageBroker:
    """Get or create message broker singleton."""
    global _broker_instance
    
    if _broker_instance is None:
        with _broker_lock:
            if _broker_instance is None:
                config = config or BrokerConfig()
                
                if config.broker_type == MessageBrokerType.RABBITMQ:
                    _broker_instance = RabbitMQBroker(config)
                elif config.broker_type == MessageBrokerType.IN_MEMORY:
                    _broker_instance = InMemoryBroker(config)
                else:
                    raise ValueError(f"Unsupported broker type: {config.broker_type}")
    
    return _broker_instance


__all__ = [
    "MessageBroker",
    "RabbitMQBroker",
    "InMemoryBroker",
    "BrokerConfig",
    "Message",
    "MessageStats",
    "MessageBrokerType",
    "MessagePriority",
    "MessageStatus",
    "get_message_broker",
]
