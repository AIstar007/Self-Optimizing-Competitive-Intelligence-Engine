"""
Load Balancing and Service Discovery Module
Provides distributed load balancing with health checks, service registry,
and multiple load balancing algorithms for horizontal scaling.
"""

import asyncio
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    STICKY = "sticky"


class ServiceHealth(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Service instance definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    host: str = ""
    port: int = 8000
    protocol: str = "http"
    weight: int = 1
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    health_status: ServiceHealth = ServiceHealth.UNKNOWN
    connection_count: int = 0
    request_count: int = 0
    errors: int = 0
    avg_response_time: float = 0.0
    
    @property
    def url(self) -> str:
        """Get service URL."""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.health_status == ServiceHealth.HEALTHY
    
    @property
    def is_alive(self) -> bool:
        """Check if service is still alive (recent heartbeat)."""
        elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return elapsed < 30  # 30 second timeout


@dataclass
class LoadBalancerStats:
    """Load balancer statistics."""
    total_requests: int = 0
    total_errors: int = 0
    active_connections: int = 0
    max_connections: int = 0
    avg_response_time: float = 0.0
    service_count: int = 0
    healthy_services: int = 0
    degraded_services: int = 0
    unhealthy_services: int = 0
    last_request: Optional[datetime] = None


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    enabled: bool = True
    interval_seconds: int = 10
    timeout_seconds: int = 5
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    method: str = "GET"
    path: str = "/health"
    expected_status: int = 200


class ServiceRegistry:
    """Registry of available service instances."""
    
    def __init__(self):
        """Initialize service registry."""
        self._instances: Dict[str, List[ServiceInstance]] = {}
        self._registry: Dict[str, ServiceInstance] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, instance: ServiceInstance) -> None:
        """Register service instance."""
        async with self._lock:
            self._registry[instance.id] = instance
            
            if instance.name not in self._instances:
                self._instances[instance.name] = []
            self._instances[instance.name].append(instance)
        
        logger.info(
            f"Registered service {instance.name} "
            f"at {instance.url} (ID: {instance.id})"
        )
    
    async def deregister(self, instance_id: str) -> bool:
        """Deregister service instance."""
        async with self._lock:
            if instance_id not in self._registry:
                return False
            
            instance = self._registry.pop(instance_id)
            if instance.name in self._instances:
                self._instances[instance.name] = [
                    i for i in self._instances[instance.name]
                    if i.id != instance_id
                ]
            
            logger.info(f"Deregistered service instance {instance_id}")
            return True
    
    async def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        """Get instance by ID."""
        async with self._lock:
            return self._registry.get(instance_id)
    
    async def get_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get all instances of a service."""
        async with self._lock:
            return self._instances.get(service_name, [])
    
    async def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances of a service."""
        instances = await self.get_instances(service_name)
        return [i for i in instances if i.is_healthy and i.is_alive]
    
    async def update_health(
        self,
        instance_id: str,
        health_status: ServiceHealth
    ) -> bool:
        """Update instance health status."""
        async with self._lock:
            if instance_id in self._registry:
                self._registry[instance_id].health_status = health_status
                self._registry[instance_id].last_heartbeat = datetime.utcnow()
                return True
        return False
    
    async def list_all(self) -> List[ServiceInstance]:
        """List all registered instances."""
        async with self._lock:
            return list(self._registry.values())
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        async with self._lock:
            instances = list(self._registry.values())
            healthy = sum(1 for i in instances if i.is_healthy)
            degraded = sum(1 for i in instances if i.health_status == ServiceHealth.DEGRADED)
            unhealthy = sum(1 for i in instances if i.health_status == ServiceHealth.UNHEALTHY)
            
            return {
                'total_instances': len(instances),
                'healthy_instances': healthy,
                'degraded_instances': degraded,
                'unhealthy_instances': unhealthy,
                'services': len(set(i.name for i in instances))
            }


class LoadBalancer:
    """Load balancer for distributing requests across service instances."""
    
    def __init__(
        self,
        registry: ServiceRegistry,
        algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN
    ):
        """Initialize load balancer."""
        self.registry = registry
        self.algorithm = algorithm
        self.stats = LoadBalancerStats()
        self._round_robin_index: Dict[str, int] = {}
        self._session_affinity: Dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def select_instance(
        self,
        service_name: str,
        client_id: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Select instance using configured algorithm."""
        instances = await self.registry.get_healthy_instances(service_name)
        
        if not instances:
            logger.warning(f"No healthy instances for service {service_name}")
            return None
        
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return await self._select_round_robin(service_name, instances)
        
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return min(instances, key=lambda i: i.connection_count)
        
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return await self._select_weighted_round_robin(service_name, instances)
        
        elif self.algorithm == LoadBalancingAlgorithm.IP_HASH and client_id:
            return instances[hash(client_id) % len(instances)]
        
        elif self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return random.choice(instances)
        
        elif self.algorithm == LoadBalancingAlgorithm.STICKY and client_id:
            return await self._select_sticky(service_name, client_id, instances)
        
        return instances[0]
    
    async def _select_round_robin(
        self,
        service_name: str,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Round-robin selection."""
        async with self._lock:
            if service_name not in self._round_robin_index:
                self._round_robin_index[service_name] = 0
            
            index = self._round_robin_index[service_name]
            selected = instances[index % len(instances)]
            self._round_robin_index[service_name] = (index + 1) % len(instances)
        
        return selected
    
    async def _select_weighted_round_robin(
        self,
        service_name: str,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Weighted round-robin selection."""
        total_weight = sum(i.weight for i in instances)
        weights = [i.weight / total_weight for i in instances]
        return random.choices(instances, weights=weights, k=1)[0]
    
    async def _select_sticky(
        self,
        service_name: str,
        client_id: str,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Sticky session selection."""
        session_key = f"{service_name}:{client_id}"
        
        async with self._lock:
            if session_key in self._session_affinity:
                instance_id = self._session_affinity[session_key]
                for instance in instances:
                    if instance.id == instance_id:
                        return instance
            
            selected = random.choice(instances)
            self._session_affinity[session_key] = selected.id
        
        return selected
    
    async def record_request(
        self,
        instance: ServiceInstance,
        success: bool,
        response_time: float
    ) -> None:
        """Record request metrics."""
        async with self._lock:
            self.stats.total_requests += 1
            if not success:
                self.stats.total_errors += 1
            
            instance.request_count += 1
            if not success:
                instance.errors += 1
            
            # Update average response time
            old_avg = instance.avg_response_time
            instance.avg_response_time = (
                (old_avg * (instance.request_count - 1) + response_time)
                / instance.request_count
            )
            
            self.stats.last_request = datetime.utcnow()
    
    async def get_stats(self) -> LoadBalancerStats:
        """Get load balancer statistics."""
        stats = await self.registry.get_stats()
        self.stats.service_count = stats.get('services', 0)
        self.stats.healthy_services = stats.get('healthy_instances', 0)
        self.stats.degraded_services = stats.get('degraded_instances', 0)
        self.stats.unhealthy_services = stats.get('unhealthy_instances', 0)
        
        return self.stats


class HealthChecker:
    """Performs health checks on service instances."""
    
    def __init__(
        self,
        registry: ServiceRegistry,
        config: Optional[HealthCheckConfig] = None
    ):
        """Initialize health checker."""
        self.registry = registry
        self.config = config or HealthCheckConfig()
        self._check_task: Optional[asyncio.Task] = None
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
    
    async def start(self) -> None:
        """Start health check loop."""
        if self.config.enabled:
            self._check_task = asyncio.create_task(self._check_loop())
            logger.info("Health checker started")
    
    async def stop(self) -> None:
        """Stop health check loop."""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            logger.info("Health checker stopped")
    
    async def _check_loop(self) -> None:
        """Main health check loop."""
        while True:
            try:
                instances = await self.registry.list_all()
                
                for instance in instances:
                    is_healthy = await self._check_instance(instance)
                    
                    if is_healthy:
                        self._failure_counts[instance.id] = 0
                        self._success_counts[instance.id] = (
                            self._success_counts.get(instance.id, 0) + 1
                        )
                        
                        if (self._success_counts[instance.id] >=
                            self.config.healthy_threshold):
                            await self.registry.update_health(
                                instance.id,
                                ServiceHealth.HEALTHY
                            )
                    else:
                        self._success_counts[instance.id] = 0
                        self._failure_counts[instance.id] = (
                            self._failure_counts.get(instance.id, 0) + 1
                        )
                        
                        if (self._failure_counts[instance.id] >=
                            self.config.unhealthy_threshold):
                            await self.registry.update_health(
                                instance.id,
                                ServiceHealth.UNHEALTHY
                            )
                
                await asyncio.sleep(self.config.interval_seconds)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.config.interval_seconds)
    
    async def _check_instance(self, instance: ServiceInstance) -> bool:
        """Check health of single instance."""
        try:
            import aiohttp
            
            url = f"{instance.url}{self.config.path}"
            timeout = aiohttp.ClientTimeout(seconds=self.config.timeout_seconds)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    self.config.method,
                    url
                ) as response:
                    return response.status == self.config.expected_status
        
        except Exception as e:
            logger.debug(f"Health check failed for {instance.id}: {e}")
            return False


# Singleton instances
_registry: Optional[ServiceRegistry] = None
_load_balancer: Optional[LoadBalancer] = None
_health_checker: Optional[HealthChecker] = None
_instance_lock = Lock()


async def get_service_registry() -> ServiceRegistry:
    """Get or create service registry singleton."""
    global _registry
    
    if _registry is None:
        with _instance_lock:
            if _registry is None:
                _registry = ServiceRegistry()
    
    return _registry


async def get_load_balancer(
    algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN
) -> LoadBalancer:
    """Get or create load balancer singleton."""
    global _load_balancer
    
    if _load_balancer is None:
        with _instance_lock:
            if _load_balancer is None:
                registry = await get_service_registry()
                _load_balancer = LoadBalancer(registry, algorithm)
    
    return _load_balancer


async def get_health_checker(
    config: Optional[HealthCheckConfig] = None
) -> HealthChecker:
    """Get or create health checker singleton."""
    global _health_checker
    
    if _health_checker is None:
        with _instance_lock:
            if _health_checker is None:
                registry = await get_service_registry()
                _health_checker = HealthChecker(registry, config)
                await _health_checker.start()
    
    return _health_checker


__all__ = [
    "ServiceRegistry",
    "LoadBalancer",
    "HealthChecker",
    "ServiceInstance",
    "LoadBalancerStats",
    "HealthCheckConfig",
    "LoadBalancingAlgorithm",
    "ServiceHealth",
    "get_service_registry",
    "get_load_balancer",
    "get_health_checker",
]
