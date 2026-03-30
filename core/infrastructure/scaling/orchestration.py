"""
Horizontal Scaling and Orchestration Module
Manages container orchestration, auto-scaling policies, and multi-instance coordination.
Supports dynamic scaling based on metrics thresholds.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class ScalingMetric(Enum):
    """Metrics used for scaling decisions."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    REQUEST_RATE = "request_rate"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    QUEUE_LENGTH = "queue_length"


class ScalingAction(Enum):
    """Auto-scaling actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"


@dataclass
class ScalingPolicy:
    """Policy for horizontal scaling."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    metric: ScalingMetric = ScalingMetric.CPU_USAGE
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 20.0
    min_instances: int = 1
    max_instances: int = 10
    scale_up_increment: int = 1
    scale_down_increment: int = 1
    cooldown_seconds: int = 300
    enabled: bool = True
    evaluation_periods: int = 2
    datapoints_to_alarm: int = 2
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'service_name': self.service_name,
            'metric': self.metric.value,
            'scale_up_threshold': self.scale_up_threshold,
            'scale_down_threshold': self.scale_down_threshold,
            'min_instances': self.min_instances,
            'max_instances': self.max_instances,
            'scale_up_increment': self.scale_up_increment,
            'scale_down_increment': self.scale_down_increment,
            'cooldown_seconds': self.cooldown_seconds,
            'enabled': self.enabled
        }


@dataclass
class ScalingEvent:
    """Record of a scaling event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    action: ScalingAction = ScalingAction.MAINTAIN
    previous_count: int = 0
    new_count: int = 0
    policy_id: Optional[str] = None
    metric_value: float = 0.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'service_name': self.service_name,
            'action': self.action.value,
            'previous_count': self.previous_count,
            'new_count': self.new_count,
            'policy_id': self.policy_id,
            'metric_value': self.metric_value,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success
        }


@dataclass
class InstanceDeployment:
    """Instance deployment information."""
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    image: str = ""
    version: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    resources: Dict[str, str] = field(default_factory=dict)
    deployed_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "running"


@dataclass
class OrchestrationStats:
    """Statistics for orchestration."""
    total_instances: int = 0
    running_instances: int = 0
    pending_instances: int = 0
    failed_instances: int = 0
    scaling_events: int = 0
    last_scaling_event: Optional[datetime] = None
    total_policy_violations: int = 0


class ScalingOrchestrator:
    """Orchestrates horizontal scaling of services."""
    
    def __init__(self):
        """Initialize scaling orchestrator."""
        self._policies: Dict[str, ScalingPolicy] = {}
        self._current_instances: Dict[str, int] = {}
        self._scaling_events: List[ScalingEvent] = []
        self._deployments: Dict[str, List[InstanceDeployment]] = {}
        self._last_scaling_time: Dict[str, datetime] = {}
        self._metric_history: Dict[str, List[float]] = {}
        self._scaling_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.stats = OrchestrationStats()
    
    async def start(self) -> None:
        """Start the scaling orchestrator."""
        self._scaling_task = asyncio.create_task(self._scaling_loop())
        logger.info("Scaling orchestrator started")
    
    async def stop(self) -> None:
        """Stop the scaling orchestrator."""
        if self._scaling_task:
            self._scaling_task.cancel()
            try:
                await self._scaling_task
            except asyncio.CancelledError:
                pass
        logger.info("Scaling orchestrator stopped")
    
    async def add_policy(self, policy: ScalingPolicy) -> str:
        """Add scaling policy."""
        async with self._lock:
            self._policies[policy.id] = policy
            self._current_instances[policy.service_name] = policy.min_instances
            self._metric_history[policy.service_name] = []
        
        logger.info(f"Added scaling policy {policy.id} for {policy.service_name}")
        return policy.id
    
    async def update_policy(self, policy: ScalingPolicy) -> bool:
        """Update scaling policy."""
        async with self._lock:
            if policy.id in self._policies:
                self._policies[policy.id] = policy
                return True
        return False
    
    async def remove_policy(self, policy_id: str) -> bool:
        """Remove scaling policy."""
        async with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
        return False
    
    async def get_policy(self, policy_id: str) -> Optional[ScalingPolicy]:
        """Get policy by ID."""
        async with self._lock:
            return self._policies.get(policy_id)
    
    async def get_policies(self) -> List[ScalingPolicy]:
        """Get all policies."""
        async with self._lock:
            return list(self._policies.values())
    
    async def record_metric(self, service_name: str, metric_value: float) -> None:
        """Record metric value for scaling evaluation."""
        async with self._lock:
            if service_name not in self._metric_history:
                self._metric_history[service_name] = []
            
            self._metric_history[service_name].append(metric_value)
            
            # Keep only last 100 readings
            if len(self._metric_history[service_name]) > 100:
                self._metric_history[service_name].pop(0)
    
    async def get_instance_count(self, service_name: str) -> int:
        """Get current instance count for service."""
        async with self._lock:
            return self._current_instances.get(service_name, 0)
    
    async def scale_service(
        self,
        service_name: str,
        target_count: int,
        reason: str = ""
    ) -> ScalingEvent:
        """Scale service to target count."""
        async with self._lock:
            policy = None
            for p in self._policies.values():
                if p.service_name == service_name:
                    policy = p
                    break
            
            if not policy:
                raise ValueError(f"No policy found for service {service_name}")
            
            # Enforce limits
            target_count = max(policy.min_instances, min(
                target_count,
                policy.max_instances
            ))
            
            previous_count = self._current_instances.get(service_name, 0)
            
            if target_count == previous_count:
                action = ScalingAction.MAINTAIN
            elif target_count > previous_count:
                action = ScalingAction.SCALE_UP
            else:
                action = ScalingAction.SCALE_DOWN
            
            event = ScalingEvent(
                service_name=service_name,
                action=action,
                previous_count=previous_count,
                new_count=target_count,
                policy_id=policy.id,
                reason=reason
            )
            
            try:
                # Simulate instance launch/termination
                await self._execute_scaling(service_name, target_count)
                
                self._current_instances[service_name] = target_count
                self._last_scaling_time[service_name] = datetime.utcnow()
                self._scaling_events.append(event)
                self.stats.scaling_events += 1
                self.stats.last_scaling_event = datetime.utcnow()
                
                logger.info(
                    f"Scaled {service_name} from {previous_count} to {target_count} "
                    f"instances ({reason})"
                )
            
            except Exception as e:
                event.success = False
                event.error = str(e)
                logger.error(f"Failed to scale {service_name}: {e}")
        
        return event
    
    async def _execute_scaling(self, service_name: str, target_count: int) -> None:
        """Execute scaling operation (placeholder for actual orchestration)."""
        if service_name not in self._deployments:
            self._deployments[service_name] = []
        
        current_deployments = self._deployments[service_name]
        
        if len(current_deployments) < target_count:
            # Scale up: add instances
            new_instances = target_count - len(current_deployments)
            for _ in range(new_instances):
                deployment = InstanceDeployment(
                    service_name=service_name,
                    image=f"{service_name}:latest",
                    version="latest"
                )
                current_deployments.append(deployment)
        
        elif len(current_deployments) > target_count:
            # Scale down: remove instances
            excess = len(current_deployments) - target_count
            self._deployments[service_name] = current_deployments[:-excess]
    
    async def _scaling_loop(self) -> None:
        """Main scaling evaluation loop."""
        while True:
            try:
                async with self._lock:
                    policies = list(self._policies.values())
                
                for policy in policies:
                    if not policy.enabled:
                        continue
                    
                    # Check cooldown
                    last_time = self._last_scaling_time.get(
                        policy.service_name,
                        datetime.utcnow() - timedelta(seconds=policy.cooldown_seconds + 1)
                    )
                    
                    elapsed = (datetime.utcnow() - last_time).total_seconds()
                    if elapsed < policy.cooldown_seconds:
                        continue
                    
                    # Get recent metrics
                    metrics = self._metric_history.get(policy.service_name, [])
                    if len(metrics) < policy.evaluation_periods:
                        continue
                    
                    recent_metrics = metrics[-policy.evaluation_periods:]
                    avg_metric = sum(recent_metrics) / len(recent_metrics)
                    
                    # Determine scaling action
                    current_count = self._current_instances.get(
                        policy.service_name,
                        policy.min_instances
                    )
                    
                    action = ScalingAction.MAINTAIN
                    new_count = current_count
                    
                    if avg_metric > policy.scale_up_threshold:
                        new_count = min(
                            current_count + policy.scale_up_increment,
                            policy.max_instances
                        )
                        action = ScalingAction.SCALE_UP
                    
                    elif avg_metric < policy.scale_down_threshold:
                        new_count = max(
                            current_count - policy.scale_down_increment,
                            policy.min_instances
                        )
                        action = ScalingAction.SCALE_DOWN
                    
                    # Execute scaling if needed
                    if action != ScalingAction.MAINTAIN:
                        reason = (
                            f"Metric {policy.metric.value} = {avg_metric:.2f} "
                            f"{'>' if action == ScalingAction.SCALE_UP else '<'} "
                            f"{'up' if action == ScalingAction.SCALE_UP else 'down'} "
                            f"threshold"
                        )
                        await self.scale_service(
                            policy.service_name,
                            new_count,
                            reason
                        )
                
                await asyncio.sleep(10)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scaling orchestrator error: {e}")
                await asyncio.sleep(10)
    
    async def get_scaling_events(
        self,
        service_name: Optional[str] = None
    ) -> List[ScalingEvent]:
        """Get scaling events."""
        events = self._scaling_events
        
        if service_name:
            events = [e for e in events if e.service_name == service_name]
        
        return events[-100:]  # Last 100 events
    
    async def get_stats(self) -> OrchestrationStats:
        """Get orchestration statistics."""
        async with self._lock:
            total_instances = sum(self._current_instances.values())
            running_instances = sum(
                len(deployments)
                for deployments in self._deployments.values()
            )
            
            self.stats.total_instances = total_instances
            self.stats.running_instances = running_instances
        
        return self.stats


# Singleton instance
_orchestrator: Optional[ScalingOrchestrator] = None
_orchestrator_lock = Lock()


async def get_scaling_orchestrator() -> ScalingOrchestrator:
    """Get or create scaling orchestrator singleton."""
    global _orchestrator
    
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = ScalingOrchestrator()
                await _orchestrator.start()
    
    return _orchestrator


__all__ = [
    "ScalingOrchestrator",
    "ScalingPolicy",
    "ScalingEvent",
    "InstanceDeployment",
    "OrchestrationStats",
    "ScalingMetric",
    "ScalingAction",
    "get_scaling_orchestrator",
]
