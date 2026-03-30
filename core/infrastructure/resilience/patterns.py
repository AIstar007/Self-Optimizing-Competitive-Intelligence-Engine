"""
Resilience Patterns Module
Implements circuit breaker pattern, bulkhead isolation, timeout handling,
and fallback strategies for fault tolerance.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class FallbackStrategy(Enum):
    """Fallback strategies when primary fails."""
    FAIL_FAST = "fail_fast"
    CACHE_FALLBACK = "cache_fallback"
    DEFAULT_VALUE = "default_value"
    DEGRADED = "degraded"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Failures to open circuit
    success_threshold: int = 2  # Successes to close circuit
    timeout_seconds: int = 60  # Time in OPEN state
    half_open_max_calls: int = 3  # Calls allowed in HALF_OPEN
    window_size: int = 10  # Rolling window size


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics."""
    state: CircuitState = CircuitState.CLOSED
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    state_changes: int = 0
    half_open_calls: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.successful_calls + self.failed_calls
        return self.successful_calls / total if total > 0 else 0.0


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker."""
        self.config = config
        self.metrics = CircuitBreakerMetrics()
        self._state = CircuitState.CLOSED
        self._last_state_change = datetime.utcnow()
        self._call_history: List[bool] = []
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def call(
        self,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            current_state = self._state
        
        # Check if circuit should transition
        if current_state == CircuitState.OPEN:
            elapsed = (datetime.utcnow() - self._last_state_change).total_seconds()
            if elapsed >= self.config.timeout_seconds:
                await self._transition(CircuitState.HALF_OPEN)
                current_state = CircuitState.HALF_OPEN
        
        if current_state == CircuitState.OPEN:
            raise Exception(f"Circuit breaker OPEN - service unavailable")
        
        if current_state == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise Exception("Half-open circuit at max calls")
                self._half_open_calls += 1
                self.metrics.half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        
        except Exception as e:
            await self._record_failure()
            raise
    
    async def _record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.total_calls += 1
            self._call_history.append(True)
            
            if len(self._call_history) > self.config.window_size:
                self._call_history.pop(0)
            
            # Transition from HALF_OPEN to CLOSED
            if self._state == CircuitState.HALF_OPEN:
                successes = sum(1 for x in self._call_history[-self.config.success_threshold:] if x)
                if successes >= self.config.success_threshold:
                    await self._transition(CircuitState.CLOSED)
    
    async def _record_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.total_calls += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self._call_history.append(False)
            
            if len(self._call_history) > self.config.window_size:
                self._call_history.pop(0)
            
            # Check if should open circuit
            if self._state == CircuitState.CLOSED:
                failures = sum(1 for x in self._call_history if not x)
                if failures >= self.config.failure_threshold:
                    await self._transition(CircuitState.OPEN)
            
            # HALF_OPEN fails immediately
            elif self._state == CircuitState.HALF_OPEN:
                await self._transition(CircuitState.OPEN)
    
    async def _transition(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        async with self._lock:
            old_state = self._state
            self._state = new_state
            self._last_state_change = datetime.utcnow()
            self.metrics.state = new_state
            self.metrics.state_changes += 1
            self._half_open_calls = 0
        
        logger.info(f"Circuit breaker transition {old_state.value} → {new_state.value}")
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state."""
        async with self._lock:
            return self._state
    
    async def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        async with self._lock:
            return CircuitBreakerMetrics(
                state=self._state,
                total_calls=self.metrics.total_calls,
                successful_calls=self.metrics.successful_calls,
                failed_calls=self.metrics.failed_calls,
                last_failure_time=self.metrics.last_failure_time,
                state_changes=self.metrics.state_changes
            )


@dataclass
class BulkheadConfig:
    """Bulkhead isolation configuration."""
    name: str = "default"
    max_concurrent_calls: int = 10
    max_wait_duration_seconds: int = 30
    queue_capacity: int = 100


@dataclass
class BulkheadMetrics:
    """Bulkhead metrics."""
    active_calls: int = 0
    max_concurrent_calls: int = 0
    queued_calls: int = 0
    total_calls: int = 0
    rejected_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_wait_time: float = 0.0


class Bulkhead:
    """Bulkhead isolation pattern."""
    
    def __init__(self, config: BulkheadConfig):
        """Initialize bulkhead."""
        self.config = config
        self.metrics = BulkheadMetrics(max_concurrent_calls=config.max_concurrent_calls)
        self._semaphore = asyncio.Semaphore(config.max_concurrent_calls)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_capacity)
        self._lock = asyncio.Lock()
        self._wait_times: List[float] = []
    
    async def execute(
        self,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> Any:
        """Execute function with bulkhead isolation."""
        # Check queue capacity
        if self._queue.full():
            async with self._lock:
                self.metrics.rejected_calls += 1
            raise Exception(f"Bulkhead {self.config.name} queue full")
        
        start_wait = time.time()
        
        try:
            # Acquire semaphore with timeout
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.max_wait_duration_seconds
            )
            
            if acquired:
                wait_time = time.time() - start_wait
                async with self._lock:
                    self.metrics.active_calls += 1
                    self.metrics.total_calls += 1
                    self._wait_times.append(wait_time)
                    if len(self._wait_times) > 100:
                        self._wait_times.pop(0)
                    self.metrics.avg_wait_time = sum(self._wait_times) / len(self._wait_times)
                
                try:
                    result = await func(*args, **kwargs)
                    async with self._lock:
                        self.metrics.successful_calls += 1
                    return result
                
                except Exception as e:
                    async with self._lock:
                        self.metrics.failed_calls += 1
                    raise
                
                finally:
                    self._semaphore.release()
                    async with self._lock:
                        self.metrics.active_calls -= 1
        
        except asyncio.TimeoutError:
            async with self._lock:
                self.metrics.rejected_calls += 1
            raise Exception(f"Bulkhead {self.config.name} timeout")
    
    async def get_metrics(self) -> BulkheadMetrics:
        """Get bulkhead metrics."""
        async with self._lock:
            return BulkheadMetrics(
                active_calls=self.metrics.active_calls,
                max_concurrent_calls=self.config.max_concurrent_calls,
                total_calls=self.metrics.total_calls,
                rejected_calls=self.metrics.rejected_calls,
                successful_calls=self.metrics.successful_calls,
                failed_calls=self.metrics.failed_calls,
                avg_wait_time=self.metrics.avg_wait_time
            )


class Resilience:
    """Composite resilience handler."""
    
    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        bulkhead: Optional[Bulkhead] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize resilience handler."""
        self.circuit_breaker = circuit_breaker
        self.bulkhead = bulkhead
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def execute(
        self,
        func: Callable[..., Coroutine],
        *args,
        fallback: Optional[Callable[..., Coroutine]] = None,
        **kwargs
    ) -> Any:
        """Execute with full resilience."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Try circuit breaker
                if self.circuit_breaker:
                    func_to_call = lambda: self.circuit_breaker.call(
                        func,
                        *args,
                        **kwargs
                    )
                else:
                    func_to_call = lambda: func(*args, **kwargs)
                
                # Try bulkhead
                if self.bulkhead:
                    result = await self.bulkhead.execute(func_to_call)
                else:
                    result = await func_to_call()
                
                # Apply timeout
                result = await asyncio.wait_for(result, timeout=self.timeout)
                
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(f"Resilience attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        # Try fallback
        if fallback:
            try:
                return await fallback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
        
        raise last_error or Exception("All resilience attempts failed")


class ResilienceManager:
    """Manages multiple resilience patterns."""
    
    def __init__(self):
        """Initialize resilience manager."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._bulkheads: Dict[str, Bulkhead] = {}
        self._resilience_handlers: Dict[str, Resilience] = {}
        self._lock = Lock()
    
    def add_circuit_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig
    ) -> CircuitBreaker:
        """Add circuit breaker."""
        with self._lock:
            cb = CircuitBreaker(config)
            self._circuit_breakers[name] = cb
        return cb
    
    def add_bulkhead(
        self,
        name: str,
        config: BulkheadConfig
    ) -> Bulkhead:
        """Add bulkhead."""
        with self._lock:
            bh = Bulkhead(config)
            self._bulkheads[name] = bh
        return bh
    
    def add_resilience(
        self,
        name: str,
        circuit_breaker: Optional[CircuitBreaker] = None,
        bulkhead: Optional[Bulkhead] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ) -> Resilience:
        """Add resilience handler."""
        with self._lock:
            resilience = Resilience(
                circuit_breaker=circuit_breaker,
                bulkhead=bulkhead,
                timeout=timeout,
                max_retries=max_retries
            )
            self._resilience_handlers[name] = resilience
        return resilience
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._circuit_breakers.get(name)
    
    def get_bulkhead(self, name: str) -> Optional[Bulkhead]:
        """Get bulkhead by name."""
        return self._bulkheads.get(name)
    
    def get_resilience(self, name: str) -> Optional[Resilience]:
        """Get resilience handler by name."""
        return self._resilience_handlers.get(name)
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics from all patterns."""
        metrics = {}
        
        for name, cb in self._circuit_breakers.items():
            cb_metrics = await cb.get_metrics()
            metrics[f"circuit_breaker:{name}"] = {
                'state': cb_metrics.state.value,
                'success_rate': cb_metrics.success_rate,
                'total_calls': cb_metrics.total_calls,
                'rejected_calls': cb_metrics.rejected_calls
            }
        
        for name, bh in self._bulkheads.items():
            bh_metrics = await bh.get_metrics()
            metrics[f"bulkhead:{name}"] = {
                'active_calls': bh_metrics.active_calls,
                'rejected_calls': bh_metrics.rejected_calls,
                'avg_wait_time': bh_metrics.avg_wait_time
            }
        
        return metrics


_manager: Optional[ResilienceManager] = None
_manager_lock = Lock()


async def get_resilience_manager() -> ResilienceManager:
    """Get or create resilience manager singleton."""
    global _manager
    
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ResilienceManager()
    
    return _manager


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitState",
    "Bulkhead",
    "BulkheadConfig",
    "BulkheadMetrics",
    "Resilience",
    "ResilienceManager",
    "FallbackStrategy",
    "get_resilience_manager",
]
