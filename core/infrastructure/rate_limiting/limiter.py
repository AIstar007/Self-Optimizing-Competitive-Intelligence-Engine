"""
Rate Limiting and Quota Management Module
Implements token bucket, sliding window, and quota-based rate limiting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class QuotaType(Enum):
    """Quota period types."""
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    CUSTOM = "custom"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    rate: int = 100  # Requests per period
    period_seconds: int = 60  # Time period
    burst_size: int = 100  # Max burst for token bucket


@dataclass
class RateLimitMetrics:
    """Rate limiting metrics."""
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    current_tokens: float = 0.0
    next_reset_time: Optional[datetime] = None
    rejection_rate: float = 0.0


class TokenBucketLimiter:
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        refill_interval_seconds: float = 1.0
    ):
        """
        Initialize token bucket limiter.
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens to add per interval
            refill_interval_seconds: Interval for token refill
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval_seconds
        self.tokens = capacity
        self.last_refill = time.time()
        self.metrics = RateLimitMetrics(current_tokens=capacity)
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: float = 1.0) -> bool:
        """Try to acquire tokens."""
        async with self._lock:
            await self._refill()
            
            self.metrics.total_requests += 1
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.metrics.allowed_requests += 1
                return True
            else:
                self.metrics.rejected_requests += 1
                return False
    
    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        refills = elapsed / self.refill_interval
        tokens_to_add = refills * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        self.metrics.current_tokens = self.tokens
    
    async def get_metrics(self) -> RateLimitMetrics:
        """Get limiter metrics."""
        async with self._lock:
            total = self.metrics.total_requests
            rejection_rate = (
                self.metrics.rejected_requests / total if total > 0 else 0.0
            )
            return RateLimitMetrics(
                total_requests=total,
                allowed_requests=self.metrics.allowed_requests,
                rejected_requests=self.metrics.rejected_requests,
                current_tokens=self.tokens,
                rejection_rate=rejection_rate
            )


class SlidingWindowLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize sliding window limiter."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times: list[float] = []
        self.metrics = RateLimitMetrics()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Try to acquire token."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove expired entries
            self.request_times = [t for t in self.request_times if t > cutoff]
            
            self.metrics.total_requests += 1
            
            if len(self.request_times) < self.max_requests:
                self.request_times.append(now)
                self.metrics.allowed_requests += 1
                return True
            else:
                self.metrics.rejected_requests += 1
                return False
    
    async def get_metrics(self) -> RateLimitMetrics:
        """Get limiter metrics."""
        async with self._lock:
            total = self.metrics.total_requests
            rejection_rate = (
                self.metrics.rejected_requests / total if total > 0 else 0.0
            )
            next_reset = (
                datetime.utcnow() + timedelta(seconds=self.window_seconds)
                if self.request_times else None
            )
            return RateLimitMetrics(
                total_requests=total,
                allowed_requests=self.metrics.allowed_requests,
                rejected_requests=self.metrics.rejected_requests,
                current_tokens=float(self.max_requests - len(self.request_times)),
                next_reset_time=next_reset,
                rejection_rate=rejection_rate
            )


class FixedWindowLimiter:
    """Fixed window rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize fixed window limiter."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_count = 0
        self.window_start = time.time()
        self.metrics = RateLimitMetrics()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Try to acquire token."""
        async with self._lock:
            now = time.time()
            
            # Check if window expired
            if now - self.window_start >= self.window_seconds:
                self.request_count = 0
                self.window_start = now
            
            self.metrics.total_requests += 1
            
            if self.request_count < self.max_requests:
                self.request_count += 1
                self.metrics.allowed_requests += 1
                return True
            else:
                self.metrics.rejected_requests += 1
                return False
    
    async def get_metrics(self) -> RateLimitMetrics:
        """Get limiter metrics."""
        async with self._lock:
            total = self.metrics.total_requests
            rejection_rate = (
                self.metrics.rejected_requests / total if total > 0 else 0.0
            )
            next_reset = datetime.utcnow() + timedelta(
                seconds=self.window_seconds - (time.time() - self.window_start)
            )
            return RateLimitMetrics(
                total_requests=total,
                allowed_requests=self.metrics.allowed_requests,
                rejected_requests=self.metrics.rejected_requests,
                current_tokens=float(self.max_requests - self.request_count),
                next_reset_time=next_reset,
                rejection_rate=rejection_rate
            )


@dataclass
class QuotaConfig:
    """Quota configuration."""
    name: str
    quota_type: QuotaType = QuotaType.PER_DAY
    max_usage: int = 1000
    custom_period_seconds: int = 86400  # For CUSTOM type


@dataclass
class QuotaMetrics:
    """Quota metrics."""
    remaining: int = 0
    used: int = 0
    limit: int = 0
    reset_time: Optional[datetime] = None
    usage_percentage: float = 0.0


class QuotaManager:
    """Manages quotas for resources."""
    
    def __init__(self):
        """Initialize quota manager."""
        self._quotas: Dict[str, Dict[str, "ClientQuota"]] = {}
        self._lock = Lock()
    
    def add_quota(
        self,
        resource: str,
        client_id: str,
        config: QuotaConfig
    ) -> "ClientQuota":
        """Add quota for client."""
        with self._lock:
            if resource not in self._quotas:
                self._quotas[resource] = {}
            
            quota = ClientQuota(config)
            self._quotas[resource][client_id] = quota
            return quota
    
    async def check_quota(
        self,
        resource: str,
        client_id: str,
        amount: int = 1
    ) -> bool:
        """Check if usage is within quota."""
        with self._lock:
            if resource not in self._quotas or client_id not in self._quotas[resource]:
                return True
        
        quota = self._quotas[resource][client_id]
        return await quota.consume(amount)
    
    async def get_quota_metrics(
        self,
        resource: str,
        client_id: str
    ) -> QuotaMetrics:
        """Get quota metrics."""
        if resource not in self._quotas or client_id not in self._quotas[resource]:
            return QuotaMetrics()
        
        quota = self._quotas[resource][client_id]
        return await quota.get_metrics()
    
    def remove_quota(self, resource: str, client_id: str) -> None:
        """Remove quota for client."""
        with self._lock:
            if resource in self._quotas:
                self._quotas[resource].pop(client_id, None)


class ClientQuota:
    """Per-client quota tracker."""
    
    def __init__(self, config: QuotaConfig):
        """Initialize client quota."""
        self.config = config
        self.used = 0
        self.period_start = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def consume(self, amount: int = 1) -> bool:
        """Consume quota."""
        async with self._lock:
            await self._check_period_reset()
            
            if self.used + amount <= self.config.max_usage:
                self.used += amount
                return True
            else:
                return False
    
    async def _check_period_reset(self) -> None:
        """Check if period should reset."""
        now = datetime.utcnow()
        
        period_seconds = self._get_period_seconds()
        elapsed = (now - self.period_start).total_seconds()
        
        if elapsed >= period_seconds:
            self.used = 0
            self.period_start = now
    
    def _get_period_seconds(self) -> int:
        """Get period in seconds."""
        if self.config.quota_type == QuotaType.PER_SECOND:
            return 1
        elif self.config.quota_type == QuotaType.PER_MINUTE:
            return 60
        elif self.config.quota_type == QuotaType.PER_HOUR:
            return 3600
        elif self.config.quota_type == QuotaType.PER_DAY:
            return 86400
        else:
            return self.config.custom_period_seconds
    
    async def get_metrics(self) -> QuotaMetrics:
        """Get quota metrics."""
        async with self._lock:
            remaining = max(0, self.config.max_usage - self.used)
            usage_pct = (self.used / self.config.max_usage * 100) if self.config.max_usage > 0 else 0.0
            
            period_seconds = self._get_period_seconds()
            reset_time = self.period_start + timedelta(seconds=period_seconds)
            
            return QuotaMetrics(
                remaining=remaining,
                used=self.used,
                limit=self.config.max_usage,
                reset_time=reset_time,
                usage_percentage=usage_pct
            )


@dataclass
class EndpointRateLimitConfig:
    """Per-endpoint rate limit configuration."""
    endpoint: str
    method: str = "GET"
    requests_per_second: int = 100
    requests_per_minute: int = 5000
    requests_per_hour: int = 100000
    burst_size: int = 100
    enabled: bool = True


class RateLimitManager:
    """Manages rate limiting for endpoints."""
    
    def __init__(self):
        """Initialize rate limit manager."""
        self._limiters: Dict[str, Tuple[TokenBucketLimiter, SlidingWindowLimiter]] = {}
        self._endpoint_configs: Dict[str, EndpointRateLimitConfig] = {}
        self._lock = Lock()
    
    def add_endpoint_limit(self, config: EndpointRateLimitConfig) -> None:
        """Add rate limit for endpoint."""
        with self._lock:
            key = f"{config.method}:{config.endpoint}"
            self._endpoint_configs[key] = config
            
            # Create limiters
            second_limiter = TokenBucketLimiter(
                capacity=config.requests_per_second,
                refill_rate=config.requests_per_second,
                refill_interval_seconds=1.0
            )
            minute_limiter = SlidingWindowLimiter(
                max_requests=config.requests_per_minute,
                window_seconds=60
            )
            self._limiters[key] = (second_limiter, minute_limiter)
    
    async def check_limit(
        self,
        endpoint: str,
        method: str = "GET",
        client_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, str]]:
        """Check if request is within limits."""
        key = f"{method}:{endpoint}"
        
        with self._lock:
            if key not in self._limiters:
                return True, {}
        
        second_limiter, minute_limiter = self._limiters[key]
        
        second_allowed = await second_limiter.acquire()
        minute_allowed = await minute_limiter.acquire()
        
        headers = {
            'X-RateLimit-Limit': str(self._endpoint_configs[key].requests_per_minute),
            'X-RateLimit-Remaining': str(
                self._endpoint_configs[key].requests_per_minute - 
                (await minute_limiter.get_metrics()).allowed_requests
            ),
            'X-RateLimit-Reset': str(
                int((await minute_limiter.get_metrics()).next_reset_time.timestamp())
            ) if (await minute_limiter.get_metrics()).next_reset_time else '0'
        }
        
        return second_allowed and minute_allowed, headers
    
    async def get_endpoint_metrics(
        self,
        endpoint: str,
        method: str = "GET"
    ) -> Dict[str, RateLimitMetrics]:
        """Get metrics for endpoint."""
        key = f"{method}:{endpoint}"
        
        if key not in self._limiters:
            return {}
        
        second_limiter, minute_limiter = self._limiters[key]
        
        return {
            'per_second': await second_limiter.get_metrics(),
            'per_minute': await minute_limiter.get_metrics()
        }


_quota_manager: Optional[QuotaManager] = None
_quota_lock = Lock()

_rate_limit_manager: Optional[RateLimitManager] = None
_rate_limit_lock = Lock()


async def get_quota_manager() -> QuotaManager:
    """Get or create quota manager singleton."""
    global _quota_manager
    
    if _quota_manager is None:
        with _quota_lock:
            if _quota_manager is None:
                _quota_manager = QuotaManager()
    
    return _quota_manager


async def get_rate_limit_manager() -> RateLimitManager:
    """Get or create rate limit manager singleton."""
    global _rate_limit_manager
    
    if _rate_limit_manager is None:
        with _rate_limit_lock:
            if _rate_limit_manager is None:
                _rate_limit_manager = RateLimitManager()
    
    return _rate_limit_manager


__all__ = [
    "TokenBucketLimiter",
    "SlidingWindowLimiter",
    "FixedWindowLimiter",
    "QuotaManager",
    "ClientQuota",
    "RateLimitManager",
    "RateLimitConfig",
    "RateLimitMetrics",
    "QuotaConfig",
    "QuotaMetrics",
    "EndpointRateLimitConfig",
    "RateLimitStrategy",
    "QuotaType",
    "get_quota_manager",
    "get_rate_limit_manager",
]
