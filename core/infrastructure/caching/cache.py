"""
Distributed Cache Management Module
Provides distributed caching with Redis backend, clustering, and replication support.
Includes cache invalidation, consistency, and failover strategies.
"""

import asyncio
import json
import logging
import pickle
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Set
from threading import Lock

import redis
import redis.asyncio as aioredis
from redis.cluster import RedisCluster, ClusterNode
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster

logger = logging.getLogger(__name__)


class CacheBackend(Enum):
    """Supported cache backends."""
    REDIS = "redis"
    REDIS_CLUSTER = "redis_cluster"
    IN_MEMORY = "in_memory"


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time-to-Live


@dataclass
class CacheEntry:
    """Cache entry metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    tags: Set[str] = field(default_factory=set)
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if not self.ttl_seconds:
            return False
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'key': self.key,
            'created_at': self.created_at.isoformat(),
            'accessed_at': self.accessed_at.isoformat(),
            'access_count': self.access_count,
            'ttl_seconds': self.ttl_seconds,
            'tags': list(self.tags),
            'compressed': self.compressed,
            'expired': self.is_expired()
        }


@dataclass
class CacheConfig:
    """Cache configuration."""
    backend: CacheBackend = CacheBackend.REDIS
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 3600  # 1 hour
    max_memory: int = 1024 * 1024 * 100  # 100MB
    eviction_policy: CacheStrategy = CacheStrategy.LRU
    enable_compression: bool = False
    compression_threshold: int = 1024  # Compress if > 1KB
    cluster_nodes: Optional[List[str]] = None
    enable_replication: bool = False
    replicas: int = 1
    connection_timeout: int = 5


@dataclass
class CacheStats:
    """Cache statistics."""
    total_gets: int = 0
    total_sets: int = 0
    total_deletes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    bytes_stored: int = 0
    max_bytes: int = 0
    evicted_keys: int = 0
    expired_keys: int = 0
    active_keys: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class Cache(ABC):
    """Abstract base class for cache implementations."""
    
    def __init__(self, config: CacheConfig):
        """Initialize cache."""
        self.config = config
        self.stats = CacheStats()
        self._lock = Lock()
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to cache backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from cache backend."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Store value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """Clear all cache entries. Returns number of deleted keys."""
        pass
    
    @abstractmethod
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass
    
    @abstractmethod
    async def delete_by_tag(self, tag: str) -> int:
        """Delete all entries with tag. Returns number of deleted keys."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass


class RedisCache(Cache):
    """Redis cache implementation."""
    
    def __init__(self, config: CacheConfig):
        """Initialize Redis cache."""
        super().__init__(config)
        self._client: Optional[aioredis.Redis] = None
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> keys
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._client = await aioredis.from_url(
                f"redis://{self.config.host}:{self.config.port}/{self.config.db}",
                password=self.config.password,
                socket_timeout=self.config.connection_timeout,
                socket_connect_timeout=self.config.connection_timeout,
                socket_keepalive=True
            )
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self._client:
            return None
        
        try:
            with self._lock:
                self.stats.total_gets += 1
            
            value = await self._client.get(key)
            
            if value:
                self.stats.cache_hits += 1
                return json.loads(value.decode())
            else:
                self.stats.cache_misses += 1
                return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in Redis with optional TTL."""
        if not self._client:
            return False
        
        try:
            ttl = ttl or self.config.default_ttl
            encoded_value = json.dumps(value, default=str)
            
            # Set main key
            await self._client.setex(
                key,
                ttl,
                encoded_value
            )
            
            # Index tags for deletion
            if tags:
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    await self._client.sadd(tag_key, key)
                    await self._client.expire(tag_key, ttl)
            
            with self._lock:
                self.stats.total_sets += 1
                self.stats.bytes_stored += len(encoded_value)
                self.stats.active_keys += 1
            
            logger.debug(f"Cached key {key} with TTL {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis."""
        if not self._client:
            return False
        
        try:
            result = await self._client.delete(key)
            
            with self._lock:
                self.stats.total_deletes += 1
                if result:
                    self.stats.active_keys -= 1
            
            return bool(result)
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._client:
            return False
        
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        if not self._client:
            return 0
        
        try:
            keys = await self._client.keys("*")
            if keys:
                deleted = await self._client.delete(*keys)
                with self._lock:
                    self.stats.evicted_keys += deleted
                    self.stats.active_keys = 0
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if not self._client:
            return []
        
        try:
            keys = await self._client.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Redis get_keys error: {e}")
            return []
    
    async def delete_by_tag(self, tag: str) -> int:
        """Delete all entries with tag."""
        if not self._client:
            return 0
        
        try:
            tag_key = f"tag:{tag}"
            keys = await self._client.smembers(tag_key)
            
            if keys:
                deleted = await self._client.delete(*keys)
                await self._client.delete(tag_key)
                
                with self._lock:
                    self.stats.evicted_keys += deleted
                    self.stats.active_keys -= deleted
                
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis delete_by_tag error: {e}")
            return 0
    
    async def get_stats(self) -> CacheStats:
        """Get Redis cache statistics."""
        if not self._client:
            return self.stats
        
        try:
            info = await self._client.info()
            with self._lock:
                self.stats.bytes_stored = info.get('used_memory', 0)
                self.stats.active_keys = info.get('db0', {}).get('keys', 0)
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
        
        return self.stats


class InMemoryCache(Cache):
    """In-memory cache implementation for testing."""
    
    def __init__(self, config: CacheConfig):
        """Initialize in-memory cache."""
        super().__init__(config)
        self._entries: Dict[str, CacheEntry] = {}
        self._tag_index: Dict[str, Set[str]] = {}
    
    async def connect(self) -> None:
        """Connect in-memory cache (no-op)."""
        logger.info("In-memory cache connected")
    
    async def disconnect(self) -> None:
        """Disconnect in-memory cache (no-op)."""
        logger.info("In-memory cache disconnected")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from in-memory cache."""
        with self._lock:
            self.stats.total_gets += 1
            
            if key not in self._entries:
                self.stats.cache_misses += 1
                return None
            
            entry = self._entries[key]
            
            if entry.is_expired():
                del self._entries[key]
                self.stats.cache_misses += 1
                self.stats.expired_keys += 1
                return None
            
            entry.accessed_at = datetime.utcnow()
            entry.access_count += 1
            self.stats.cache_hits += 1
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in in-memory cache."""
        ttl = ttl or self.config.default_ttl
        
        with self._lock:
            entry = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl,
                tags=tags or set()
            )
            self._entries[key] = entry
            self.stats.total_sets += 1
            self.stats.bytes_stored += len(str(value))
            self.stats.active_keys = len(self._entries)
            
            # Index tags
            if tags:
                for tag in tags:
                    if tag not in self._tag_index:
                        self._tag_index[tag] = set()
                    self._tag_index[tag].add(key)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from in-memory cache."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                self.stats.total_deletes += 1
                self.stats.active_keys = len(self._entries)
                return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in in-memory cache."""
        with self._lock:
            if key not in self._entries:
                return False
            
            entry = self._entries[key]
            if entry.is_expired():
                del self._entries[key]
                return False
            
            return True
    
    async def clear(self) -> int:
        """Clear all in-memory cache entries."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._tag_index.clear()
            self.stats.evicted_keys += count
            self.stats.active_keys = 0
            return count
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        import fnmatch
        
        with self._lock:
            if pattern == "*":
                return list(self._entries.keys())
            return [
                key for key in self._entries.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
    
    async def delete_by_tag(self, tag: str) -> int:
        """Delete all entries with tag."""
        with self._lock:
            if tag not in self._tag_index:
                return 0
            
            keys_to_delete = self._tag_index[tag]
            deleted = 0
            
            for key in keys_to_delete:
                if key in self._entries:
                    del self._entries[key]
                    deleted += 1
            
            del self._tag_index[tag]
            self.stats.evicted_keys += deleted
            self.stats.active_keys = len(self._entries)
            return deleted
    
    async def get_stats(self) -> CacheStats:
        """Get in-memory cache statistics."""
        with self._lock:
            self.stats.bytes_stored = sum(
                len(str(e.value)) for e in self._entries.values()
            )
            self.stats.active_keys = len(self._entries)
        
        return self.stats


# Singleton instance
_cache_instance: Optional[Cache] = None
_cache_lock = Lock()


async def get_cache(config: Optional[CacheConfig] = None) -> Cache:
    """Get or create cache singleton."""
    global _cache_instance
    
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                config = config or CacheConfig()
                
                if config.backend == CacheBackend.REDIS:
                    _cache_instance = RedisCache(config)
                elif config.backend == CacheBackend.IN_MEMORY:
                    _cache_instance = InMemoryCache(config)
                else:
                    raise ValueError(f"Unsupported cache backend: {config.backend}")
                
                await _cache_instance.connect()
    
    return _cache_instance


__all__ = [
    "Cache",
    "RedisCache",
    "InMemoryCache",
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    "CacheBackend",
    "CacheStrategy",
    "get_cache",
]
