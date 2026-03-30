"""
Advanced Caching Strategies Module
Multi-tier caching, cache warming, coherence protocols, and write policies.
Implements L1/L2 cache architecture with synchronization strategies.
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Lock
import hashlib

logger = logging.getLogger(__name__)


class CacheCoherence(Enum):
    """Cache coherence protocols."""
    WRITE_THROUGH = "write_through"  # Write to both caches immediately
    WRITE_BACK = "write_back"  # Write to L1, async to L2
    WRITE_AROUND = "write_around"  # Skip L1, write directly to L2
    INVALIDATE = "invalidate"  # Invalidate L1 on L2 update


class CachePriority(Enum):
    """Cache priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class CacheMetrics:
    """Advanced cache metrics."""
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    write_backs_pending: int = 0
    coherence_mismatches: int = 0
    eviction_count: int = 0
    warm_count: int = 0
    sync_errors: int = 0
    coherence_latency: float = 0.0
    
    @property
    def l1_hit_rate(self) -> float:
        """Calculate L1 hit rate."""
        total = self.l1_hits + self.l1_misses
        return self.l1_hits / total if total > 0 else 0.0
    
    @property
    def l2_hit_rate(self) -> float:
        """Calculate L2 hit rate."""
        total = self.l2_hits + self.l2_misses
        return self.l2_hits / total if total > 0 else 0.0
    
    @property
    def overall_hit_rate(self) -> float:
        """Calculate overall hit rate."""
        total_hits = self.l1_hits + self.l2_hits
        total = total_hits + self.l1_misses + self.l2_misses
        return total_hits / total if total > 0 else 0.0


@dataclass
class CacheWarmingStrategy:
    """Cache warming configuration."""
    enabled: bool = True
    strategy: str = "eager"  # eager, lazy, probabilistic
    warm_on_startup: bool = True
    warm_period_seconds: int = 3600  # 1 hour
    batch_size: int = 100
    fetch_function: Optional[Callable] = None
    tags: Set[str] = field(default_factory=set)
    ttl_seconds: int = 3600
    priority: CachePriority = CachePriority.NORMAL


@dataclass
class WriteBackEntry:
    """Entry pending write-back to L2."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    attempts: int = 0
    max_attempts: int = 3


class MultiTierCache:
    """Multi-tier (L1/L2) cache with coherence protocols."""
    
    def __init__(
        self,
        l1_cache: Any,
        l2_cache: Any,
        coherence_protocol: CacheCoherence = CacheCoherence.WRITE_BACK
    ):
        """Initialize multi-tier cache."""
        self.l1 = l1_cache
        self.l2 = l2_cache
        self.coherence = coherence_protocol
        self.metrics = CacheMetrics()
        self._lock = asyncio.Lock()
        self._write_back_queue: Dict[str, WriteBackEntry] = {}
        self._l1_timestamps: Dict[str, datetime] = {}
        self._l2_timestamps: Dict[str, datetime] = {}
        self._writeback_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start multi-tier cache with write-back processing."""
        if self.coherence == CacheCoherence.WRITE_BACK:
            self._writeback_task = asyncio.create_task(self._process_writebacks())
        logger.info(f"Started multi-tier cache with {self.coherence.value}")
    
    async def stop(self) -> None:
        """Stop multi-tier cache."""
        if self._writeback_task:
            self._writeback_task.cancel()
            try:
                await self._writeback_task
            except asyncio.CancelledError:
                pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache hierarchy."""
        # Try L1 first
        l1_value = await self.l1.get(key)
        if l1_value is not None:
            async with self._lock:
                self.metrics.l1_hits += 1
            logger.debug(f"L1 hit: {key}")
            return l1_value
        
        async with self._lock:
            self.metrics.l1_misses += 1
        
        # Fall back to L2
        l2_value = await self.l2.get(key)
        if l2_value is not None:
            async with self._lock:
                self.metrics.l2_hits += 1
            
            # Populate L1 for next access
            await self.l1.set(key, l2_value)
            logger.debug(f"L2 hit, populated L1: {key}")
            return l2_value
        
        async with self._lock:
            self.metrics.l2_misses += 1
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> None:
        """Set value with coherence protocol."""
        async with self._lock:
            current_time = datetime.utcnow()
            self._l1_timestamps[key] = current_time
            self._l2_timestamps[key] = current_time
        
        if self.coherence == CacheCoherence.WRITE_THROUGH:
            await self._write_through(key, value, ttl, tags)
        
        elif self.coherence == CacheCoherence.WRITE_BACK:
            await self._write_back(key, value, ttl, tags)
        
        elif self.coherence == CacheCoherence.WRITE_AROUND:
            await self._write_around(key, value, ttl, tags)
        
        elif self.coherence == CacheCoherence.INVALIDATE:
            await self._invalidate_on_write(key, value, ttl, tags)
    
    async def _write_through(
        self,
        key: str,
        value: Any,
        ttl: Optional[int],
        tags: Optional[Set[str]]
    ) -> None:
        """Write-through: update both caches immediately."""
        await self.l1.set(key, value, ttl, tags)
        await self.l2.set(key, value, ttl, tags)
        logger.debug(f"Write-through: {key}")
    
    async def _write_back(
        self,
        key: str,
        value: Any,
        ttl: Optional[int],
        tags: Optional[Set[str]]
    ) -> None:
        """Write-back: update L1, queue for L2."""
        await self.l1.set(key, value, ttl, tags)
        
        async with self._lock:
            self._write_back_queue[key] = WriteBackEntry(
                key=key,
                value=value
            )
            self.metrics.write_backs_pending = len(self._write_back_queue)
        
        logger.debug(f"Write-back queued: {key}")
    
    async def _write_around(
        self,
        key: str,
        value: Any,
        ttl: Optional[int],
        tags: Optional[Set[str]]
    ) -> None:
        """Write-around: skip L1, write to L2 directly."""
        await self.l2.set(key, value, ttl, tags)
        # Invalidate L1 if present
        await self.l1.delete(key)
        logger.debug(f"Write-around: {key}")
    
    async def _invalidate_on_write(
        self,
        key: str,
        value: Any,
        ttl: Optional[int],
        tags: Optional[Set[str]]
    ) -> None:
        """Invalidate L1, update L2."""
        await self.l1.delete(key)
        await self.l2.set(key, value, ttl, tags)
        logger.debug(f"Invalidate-on-write: {key}")
    
    async def delete(self, key: str) -> bool:
        """Delete from both cache tiers."""
        l1_deleted = await self.l1.delete(key)
        l2_deleted = await self.l2.delete(key)
        
        async with self._lock:
            self._write_back_queue.pop(key, None)
            self._l1_timestamps.pop(key, None)
            self._l2_timestamps.pop(key, None)
        
        return l1_deleted or l2_deleted
    
    async def _process_writebacks(self) -> None:
        """Process pending write-back entries."""
        while True:
            try:
                async with self._lock:
                    entries = list(self._write_back_queue.values())
                
                for entry in entries:
                    try:
                        await self.l2.set(entry.key, entry.value)
                        
                        async with self._lock:
                            self._write_back_queue.pop(entry.key, None)
                    
                    except Exception as e:
                        logger.error(f"Write-back failed for {entry.key}: {e}")
                        entry.attempts += 1
                        
                        if entry.attempts >= entry.max_attempts:
                            async with self._lock:
                                self.metrics.sync_errors += 1
                                self._write_back_queue.pop(entry.key, None)
                
                await asyncio.sleep(5)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Write-back processor error: {e}")
    
    async def get_metrics(self) -> CacheMetrics:
        """Get cache metrics."""
        async with self._lock:
            return CacheMetrics(
                l1_hits=self.metrics.l1_hits,
                l1_misses=self.metrics.l1_misses,
                l2_hits=self.metrics.l2_hits,
                l2_misses=self.metrics.l2_misses,
                write_backs_pending=len(self._write_back_queue),
                coherence_mismatches=self.metrics.coherence_mismatches,
                sync_errors=self.metrics.sync_errors
            )


class CacheWarmer:
    """Manages cache warming strategies."""
    
    def __init__(self, cache: Any):
        """Initialize cache warmer."""
        self.cache = cache
        self._warming_tasks: Dict[str, asyncio.Task] = {}
        self._warming_stats: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def add_warming_strategy(
        self,
        strategy_name: str,
        strategy: CacheWarmingStrategy
    ) -> str:
        """Add cache warming strategy."""
        strategy_id = str(uuid.uuid4())
        
        if strategy.warm_on_startup:
            await self._warm_cache(strategy)
        
        if strategy.enabled and strategy.warm_period_seconds > 0:
            task = asyncio.create_task(
                self._periodic_warm(strategy_id, strategy)
            )
            async with self._lock:
                self._warming_tasks[strategy_id] = task
                self._warming_stats[strategy_id] = 0
        
        logger.info(f"Added warming strategy {strategy_name} ({strategy_id})")
        return strategy_id
    
    async def _warm_cache(self, strategy: CacheWarmingStrategy) -> int:
        """Warm cache with data."""
        if not strategy.fetch_function:
            return 0
        
        warmed_count = 0
        try:
            # Fetch data to warm
            data = await strategy.fetch_function()
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, tuple) and len(item) >= 2:
                        key, value = item[0], item[1]
                        await self.cache.set(
                            key,
                            value,
                            ttl=strategy.ttl_seconds,
                            tags=strategy.tags
                        )
                        warmed_count += 1
            
            logger.info(f"Cache warmed: {warmed_count} entries")
        
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
        
        return warmed_count
    
    async def _periodic_warm(
        self,
        strategy_id: str,
        strategy: CacheWarmingStrategy
    ) -> None:
        """Periodically warm cache."""
        while True:
            try:
                if strategy.enabled:
                    warmed = await self._warm_cache(strategy)
                    async with self._lock:
                        self._warming_stats[strategy_id] = warmed
                
                await asyncio.sleep(strategy.warm_period_seconds)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic warming error: {e}")
    
    async def remove_strategy(self, strategy_id: str) -> bool:
        """Remove warming strategy."""
        async with self._lock:
            task = self._warming_tasks.pop(strategy_id, None)
            self._warming_stats.pop(strategy_id, None)
        
        if task:
            task.cancel()
            return True
        return False
    
    async def get_warming_stats(self) -> Dict[str, int]:
        """Get warming statistics."""
        async with self._lock:
            return dict(self._warming_stats)


class CacheCoherencyManager:
    """Manages coherency between distributed cache instances."""
    
    def __init__(self):
        """Initialize coherency manager."""
        self._version_vectors: Dict[str, Dict[str, int]] = {}
        self._pending_syncs: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._syncs_completed: int = 0
    
    async def record_write(
        self,
        key: str,
        node_id: str,
        version: int
    ) -> None:
        """Record write operation for coherency tracking."""
        async with self._lock:
            if key not in self._version_vectors:
                self._version_vectors[key] = {}
            
            self._version_vectors[key][node_id] = version
    
    async def get_version_vector(self, key: str) -> Dict[str, int]:
        """Get version vector for key."""
        async with self._lock:
            return self._version_vectors.get(key, {})
    
    async def detect_conflicts(self, key: str) -> bool:
        """Detect version conflicts."""
        async with self._lock:
            vector = self._version_vectors.get(key, {})
            # Conflict if more than one node has written
            return len(vector) > 1
    
    async def synchronize(self, key: str, nodes: List[str]) -> None:
        """Synchronize key across nodes."""
        async with self._lock:
            self._pending_syncs[key] = set(nodes)
        
        try:
            # Simulate sync
            await asyncio.sleep(0.01)
            
            async with self._lock:
                self._pending_syncs.pop(key, None)
                self._syncs_completed += 1
        
        except Exception as e:
            logger.error(f"Synchronization error for {key}: {e}")
    
    async def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        async with self._lock:
            return {
                'syncs_completed': self._syncs_completed,
                'pending_syncs': len(self._pending_syncs),
                'tracked_keys': len(self._version_vectors)
            }


class AdaptiveCache:
    """Adaptive cache that adjusts strategies based on access patterns."""
    
    def __init__(self, base_cache: Any):
        """Initialize adaptive cache."""
        self.cache = base_cache
        self._access_patterns: Dict[str, List[float]] = {}
        self._strategy_hints: Dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def get_with_pattern_tracking(self, key: str) -> Optional[Any]:
        """Get with access pattern tracking."""
        start_time = time.time()
        value = await self.cache.get(key)
        latency = time.time() - start_time
        
        async with self._lock:
            if key not in self._access_patterns:
                self._access_patterns[key] = []
            
            self._access_patterns[key].append(latency)
            
            # Keep last 100 accesses
            if len(self._access_patterns[key]) > 100:
                self._access_patterns[key].pop(0)
        
        return value
    
    async def analyze_patterns(self) -> Dict[str, str]:
        """Analyze patterns and suggest strategies."""
        strategies = {}
        
        async with self._lock:
            for key, latencies in self._access_patterns.items():
                if not latencies:
                    continue
                
                avg_latency = sum(latencies) / len(latencies)
                variance = sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)
                
                # High variance = bursty access → use WRITE_BACK
                if variance > 0.01:
                    strategies[key] = CacheCoherence.WRITE_BACK.value
                # Consistent slow access → use WRITE_THROUGH
                elif avg_latency > 0.1:
                    strategies[key] = CacheCoherence.WRITE_THROUGH.value
                # Fast, consistent → use WRITE_AROUND
                else:
                    strategies[key] = CacheCoherence.WRITE_AROUND.value
        
        return strategies


__all__ = [
    "MultiTierCache",
    "CacheWarmer",
    "CacheCoherencyManager",
    "AdaptiveCache",
    "CacheMetrics",
    "CacheWarmingStrategy",
    "WriteBackEntry",
    "CacheCoherence",
    "CachePriority",
]
