"""
STEP 15 Distributed Processing & Scalability - Comprehensive Tests
Tests for message brokers, task workers, distributed caching, 
load balancing, and horizontal scaling orchestration.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

# Message Broker Tests
from core.infrastructure.messaging import (
    Message,
    MessageBroker,
    BrokerConfig,
    MessageBrokerType,
    MessagePriority,
    MessageStatus,
    get_message_broker,
    MessageRouter,
    MessageHandler,
    get_message_router,
)

# Task Worker Tests
from core.infrastructure.scaling import (
    WorkerPool,
    JobScheduler,
    Task,
    ScheduledJob,
    JobResult,
    JobStatus,
    TaskPriority,
    ScheduleType,
    get_worker_pool,
    get_job_scheduler,
)

# Cache Tests
from core.infrastructure.caching import (
    Cache,
    CacheConfig,
    CacheBackend,
    CacheStrategy,
    get_cache,
)

# Load Balancing Tests
from core.infrastructure.distributed import (
    ServiceRegistry,
    LoadBalancer,
    ServiceInstance,
    LoadBalancingAlgorithm,
    ServiceHealth,
    HealthCheckConfig,
    get_service_registry,
    get_load_balancer,
)

# Scaling Tests
from core.infrastructure.scaling import (
    ScalingOrchestrator,
    ScalingPolicy,
    ScalingMetric,
    ScalingAction,
    get_scaling_orchestrator,
)


# ============================================================================
# MESSAGE BROKER TESTS
# ============================================================================

class TestMessageBroker:
    """Test message broker functionality."""
    
    @pytest.mark.asyncio
    async def test_broker_creation(self):
        """Test creating message broker."""
        config = BrokerConfig(broker_type=MessageBrokerType.IN_MEMORY)
        broker = get_message_broker(config)
        assert broker is not None
        assert isinstance(broker, MessageBroker)
    
    @pytest.mark.asyncio
    async def test_message_creation(self):
        """Test creating messages."""
        message = Message(
            exchange="test_exchange",
            routing_key="test.route",
            body={"data": "test_data"},
            priority=MessagePriority.HIGH
        )
        assert message.id is not None
        assert message.routing_key == "test.route"
        assert message.priority == MessagePriority.HIGH
        assert message.status == MessageStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_message_serialization(self):
        """Test message JSON serialization."""
        message = Message(
            exchange="test",
            routing_key="test.route",
            body={"key": "value"}
        )
        json_str = message.to_json()
        assert '{"key": "value"}' in json_str or '{"key":"value"}' in json_str
    
    @pytest.mark.asyncio
    async def test_in_memory_broker_publish(self):
        """Test in-memory broker message publishing."""
        config = BrokerConfig(broker_type=MessageBrokerType.IN_MEMORY)
        broker = get_message_broker(config)
        await broker.connect()
        
        message = Message(
            exchange="test_ex",
            routing_key="test.key",
            body={"test": "data"}
        )
        
        result = await broker.publish(message)
        assert result is True
        assert message.status == MessageStatus.SENT
    
    @pytest.mark.asyncio
    async def test_message_broker_stats(self):
        """Test message broker statistics."""
        config = BrokerConfig(broker_type=MessageBrokerType.IN_MEMORY)
        broker = get_message_broker(config)
        await broker.connect()
        
        message = Message(
            exchange="test",
            routing_key="test.route",
            body={"data": "test"}
        )
        
        await broker.publish(message)
        stats = await broker.get_stats()
        
        assert stats.total_published >= 1
        assert stats.total_failed == 0


class TestMessageRouter:
    """Test message routing functionality."""
    
    @pytest.mark.asyncio
    async def test_router_creation(self):
        """Test creating message router."""
        router = await get_message_router()
        assert router is not None
        assert isinstance(router, MessageRouter)
    
    @pytest.mark.asyncio
    async def test_router_rules(self):
        """Test adding routing rules."""
        router = await get_message_router()
        
        class TestHandler(MessageHandler):
            async def can_handle(self, message: Message) -> bool:
                return True
            
            async def handle(self, message: Message) -> bool:
                message.body["processed"] = True
                return True
        
        handler = TestHandler()
        router.add_rule("test\\..*", handler, priority=1)
        
        rules = router.get_rules()
        assert len(rules) > 0
        assert any(r['pattern'] == "test\\..*" for r in rules)


# ============================================================================
# TASK WORKER AND SCHEDULING TESTS
# ============================================================================

class TestWorkerPool:
    """Test async worker pool functionality."""
    
    @pytest.mark.asyncio
    async def test_worker_pool_creation(self):
        """Test creating worker pool."""
        pool = await get_worker_pool(num_workers=2)
        assert pool is not None
        assert pool.num_workers == 2
    
    @pytest.mark.asyncio
    async def test_task_submission(self):
        """Test submitting tasks to worker pool."""
        pool = await get_worker_pool(num_workers=2)
        
        async def sample_task(x: int) -> int:
            await asyncio.sleep(0.1)
            return x * 2
        
        task = Task(
            name="sample_task",
            function=sample_task,
            args=(5,)
        )
        
        task_id = await pool.submit(task)
        assert task_id is not None
        assert task_id == task.id
    
    @pytest.mark.asyncio
    async def test_task_execution(self):
        """Test task execution and result retrieval."""
        pool = await get_worker_pool(num_workers=1)
        
        async def add_numbers(a: int, b: int) -> int:
            await asyncio.sleep(0.05)
            return a + b
        
        task = Task(
            name="add_task",
            function=add_numbers,
            args=(3, 4)
        )
        
        task_id = await pool.submit(task)
        result = await asyncio.wait_for(
            pool.get_result(task_id),
            timeout=5.0
        )
        
        assert result.status == JobStatus.COMPLETED
        assert result.result == 7
    
    @pytest.mark.asyncio
    async def test_task_priority(self):
        """Test task priority ordering."""
        pool = await get_worker_pool(num_workers=1)
        
        async def dummy_task():
            await asyncio.sleep(0.01)
            return "done"
        
        low_task = Task(
            name="low",
            function=dummy_task,
            priority=TaskPriority.LOW
        )
        
        high_task = Task(
            name="high",
            function=dummy_task,
            priority=TaskPriority.HIGH
        )
        
        # High priority should be ordered before low
        assert high_task < low_task
    
    @pytest.mark.asyncio
    async def test_worker_stats(self):
        """Test worker pool statistics."""
        pool = await get_worker_pool(num_workers=1)
        
        async def task_func():
            await asyncio.sleep(0.01)
            return "result"
        
        task = Task(name="test", function=task_func)
        await pool.submit(task)
        
        stats = pool.get_stats()
        assert stats.total_tasks >= 1


class TestJobScheduler:
    """Test job scheduling functionality."""
    
    @pytest.mark.asyncio
    async def test_scheduler_creation(self):
        """Test creating job scheduler."""
        pool = await get_worker_pool(num_workers=1)
        scheduler = await get_job_scheduler(pool)
        assert scheduler is not None
        assert isinstance(scheduler, JobScheduler)
    
    @pytest.mark.asyncio
    async def test_schedule_once(self):
        """Test scheduling one-time jobs."""
        pool = await get_worker_pool(num_workers=1)
        scheduler = await get_job_scheduler(pool)
        
        async def one_time_task():
            return "executed"
        
        task = Task(
            name="once_task",
            function=one_time_task
        )
        
        job = ScheduledJob(
            name="test_once",
            task=task,
            schedule_type=ScheduleType.ONCE,
            next_run=datetime.utcnow()
        )
        
        job_id = await scheduler.schedule_job(job)
        assert job_id is not None
    
    @pytest.mark.asyncio
    async def test_schedule_interval(self):
        """Test scheduling periodic jobs."""
        pool = await get_worker_pool(num_workers=1)
        scheduler = await get_job_scheduler(pool)
        
        async def periodic_task():
            return "periodic"
        
        task = Task(
            name="periodic_task",
            function=periodic_task
        )
        
        job = ScheduledJob(
            name="test_periodic",
            task=task,
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=5
        )
        
        job_id = await scheduler.schedule_job(job)
        assert job_id is not None
        
        # Verify job is registered
        retrieved_job = scheduler.get_job(job_id)
        assert retrieved_job is not None
        assert retrieved_job.schedule_type == ScheduleType.INTERVAL


# ============================================================================
# DISTRIBUTED CACHE TESTS
# ============================================================================

class TestDistributedCache:
    """Test distributed caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_creation(self):
        """Test creating cache."""
        config = CacheConfig(backend=CacheBackend.IN_MEMORY)
        cache = await get_cache(config)
        assert cache is not None
        assert isinstance(cache, Cache)
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test cache set and get operations."""
        config = CacheConfig(backend=CacheBackend.IN_MEMORY)
        cache = await get_cache(config)
        
        await cache.set("test_key", {"data": "test"})
        value = await cache.get("test_key")
        
        assert value is not None
        assert value == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache delete operation."""
        config = CacheConfig(backend=CacheBackend.IN_MEMORY)
        cache = await get_cache(config)
        
        await cache.set("delete_key", "value")
        exists = await cache.exists("delete_key")
        assert exists is True
        
        result = await cache.delete("delete_key")
        assert result is True
        
        exists = await cache.exists("delete_key")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_cache_tags(self):
        """Test cache tagging functionality."""
        config = CacheConfig(backend=CacheBackend.IN_MEMORY)
        cache = await get_cache(config)
        
        await cache.set("key1", "value1", tags={"user:123"})
        await cache.set("key2", "value2", tags={"user:123"})
        
        deleted = await cache.delete_by_tag("user:123")
        assert deleted == 2
        
        exists1 = await cache.exists("key1")
        exists2 = await cache.exists("key2")
        assert exists1 is False
        assert exists2 is False
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        config = CacheConfig(backend=CacheBackend.IN_MEMORY)
        cache = await get_cache(config)
        
        await cache.set("stat_key", "value")
        await cache.get("stat_key")
        await cache.get("nonexistent")
        
        stats = await cache.get_stats()
        assert stats.total_sets >= 1
        assert stats.total_gets >= 2
        assert stats.cache_hits >= 1
        assert stats.cache_misses >= 1


# ============================================================================
# LOAD BALANCING TESTS
# ============================================================================

class TestServiceRegistry:
    """Test service registry functionality."""
    
    @pytest.mark.asyncio
    async def test_register_instance(self):
        """Test registering service instances."""
        registry = await get_service_registry()
        
        instance = ServiceInstance(
            name="test_service",
            host="localhost",
            port=8000
        )
        
        await registry.register(instance)
        retrieved = await registry.get_instance(instance.id)
        
        assert retrieved is not None
        assert retrieved.name == "test_service"
    
    @pytest.mark.asyncio
    async def test_deregister_instance(self):
        """Test deregistering service instances."""
        registry = await get_service_registry()
        
        instance = ServiceInstance(
            name="deregister_test",
            host="localhost",
            port=8001
        )
        
        await registry.register(instance)
        result = await registry.deregister(instance.id)
        
        assert result is True
        retrieved = await registry.get_instance(instance.id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_get_healthy_instances(self):
        """Test getting healthy instances."""
        registry = await get_service_registry()
        
        instance1 = ServiceInstance(
            name="healthy_service",
            host="localhost",
            port=8000,
            health_status=ServiceHealth.HEALTHY
        )
        
        instance2 = ServiceInstance(
            name="healthy_service",
            host="localhost",
            port=8001,
            health_status=ServiceHealth.UNHEALTHY
        )
        
        await registry.register(instance1)
        await registry.register(instance2)
        
        healthy = await registry.get_healthy_instances("healthy_service")
        assert len(healthy) == 1
        assert healthy[0].id == instance1.id


class TestLoadBalancer:
    """Test load balancing functionality."""
    
    @pytest.mark.asyncio
    async def test_round_robin_selection(self):
        """Test round-robin load balancing."""
        registry = await get_service_registry()
        
        instance1 = ServiceInstance(
            name="lb_test",
            host="localhost",
            port=8000,
            health_status=ServiceHealth.HEALTHY
        )
        
        instance2 = ServiceInstance(
            name="lb_test",
            host="localhost",
            port=8001,
            health_status=ServiceHealth.HEALTHY
        )
        
        await registry.register(instance1)
        await registry.register(instance2)
        
        lb = await get_load_balancer(LoadBalancingAlgorithm.ROUND_ROBIN)
        
        selected1 = await lb.select_instance("lb_test")
        selected2 = await lb.select_instance("lb_test")
        
        # Should alternate between instances
        assert selected1 is not None
        assert selected2 is not None
    
    @pytest.mark.asyncio
    async def test_least_connections(self):
        """Test least connections load balancing."""
        registry = await get_service_registry()
        
        instance1 = ServiceInstance(
            name="lc_test",
            host="localhost",
            port=8000,
            health_status=ServiceHealth.HEALTHY,
            connection_count=5
        )
        
        instance2 = ServiceInstance(
            name="lc_test",
            host="localhost",
            port=8001,
            health_status=ServiceHealth.HEALTHY,
            connection_count=2
        )
        
        await registry.register(instance1)
        await registry.register(instance2)
        
        lb = await get_load_balancer(LoadBalancingAlgorithm.LEAST_CONNECTIONS)
        
        selected = await lb.select_instance("lc_test")
        assert selected is not None
        assert selected.connection_count == 2


# ============================================================================
# HORIZONTAL SCALING TESTS
# ============================================================================

class TestScalingOrchestrator:
    """Test horizontal scaling orchestration."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_creation(self):
        """Test creating scaling orchestrator."""
        orchestrator = await get_scaling_orchestrator()
        assert orchestrator is not None
        assert isinstance(orchestrator, ScalingOrchestrator)
    
    @pytest.mark.asyncio
    async def test_add_scaling_policy(self):
        """Test adding scaling policies."""
        orchestrator = await get_scaling_orchestrator()
        
        policy = ScalingPolicy(
            service_name="test_service",
            metric=ScalingMetric.CPU_USAGE,
            scale_up_threshold=80.0,
            scale_down_threshold=20.0,
            min_instances=1,
            max_instances=5
        )
        
        policy_id = await orchestrator.add_policy(policy)
        assert policy_id is not None
        
        retrieved = await orchestrator.get_policy(policy_id)
        assert retrieved is not None
        assert retrieved.service_name == "test_service"
    
    @pytest.mark.asyncio
    async def test_record_metric(self):
        """Test recording metrics for scaling."""
        orchestrator = await get_scaling_orchestrator()
        
        policy = ScalingPolicy(
            service_name="metric_test",
            metric=ScalingMetric.REQUEST_RATE,
            min_instances=1,
            max_instances=3
        )
        
        await orchestrator.add_policy(policy)
        
        # Record metrics
        await orchestrator.record_metric("metric_test", 50.0)
        await orchestrator.record_metric("metric_test", 60.0)
    
    @pytest.mark.asyncio
    async def test_scaling_events(self):
        """Test recording scaling events."""
        orchestrator = await get_scaling_orchestrator()
        
        policy = ScalingPolicy(
            service_name="event_test",
            min_instances=1,
            max_instances=5
        )
        
        await orchestrator.add_policy(policy)
        
        event = await orchestrator.scale_service(
            "event_test",
            2,
            "Test scaling"
        )
        
        assert event is not None
        assert event.service_name == "event_test"
        
        events = await orchestrator.get_scaling_events("event_test")
        assert len(events) > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for distributed processing."""
    
    @pytest.mark.asyncio
    async def test_message_broker_and_worker_integration(self):
        """Test message broker with worker pool."""
        config = BrokerConfig(broker_type=MessageBrokerType.IN_MEMORY)
        broker = get_message_broker(config)
        await broker.connect()
        
        pool = await get_worker_pool(num_workers=1)
        
        async def process_message(msg_data: Dict[str, Any]) -> str:
            await asyncio.sleep(0.01)
            return f"Processed: {msg_data.get('content')}"
        
        message = Message(
            exchange="worker_test",
            routing_key="process.task",
            body={"content": "task_data"}
        )
        
        result = await broker.publish(message)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_with_load_balancer(self):
        """Test caching with load balanced services."""
        cache_config = CacheConfig(backend=CacheBackend.IN_MEMORY)
        cache = await get_cache(cache_config)
        
        registry = await get_service_registry()
        
        instance = ServiceInstance(
            name="cached_service",
            host="localhost",
            port=8000,
            health_status=ServiceHealth.HEALTHY
        )
        
        await registry.register(instance)
        
        # Cache service data
        await cache.set(
            f"service:{instance.id}",
            instance.url,
            ttl=60
        )
        
        cached_url = await cache.get(f"service:{instance.id}")
        assert cached_url is not None
        assert cached_url == instance.url
    
    @pytest.mark.asyncio
    async def test_scaling_with_metrics(self):
        """Test scaling orchestrator with metrics recording."""
        orchestrator = await get_scaling_orchestrator()
        
        policy = ScalingPolicy(
            service_name="integrated_service",
            metric=ScalingMetric.CPU_USAGE,
            scale_up_threshold=75.0,
            scale_down_threshold=25.0,
            min_instances=2,
            max_instances=4
        )
        
        await orchestrator.add_policy(policy)
        
        # Record metrics simulating high load
        for i in range(5):
            await orchestrator.record_metric("integrated_service", 80.0 + i)
        
        # Verify metrics recorded
        current_count = await orchestrator.get_instance_count("integrated_service")
        assert current_count >= policy.min_instances


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
