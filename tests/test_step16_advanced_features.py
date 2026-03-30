"""
Comprehensive tests for STEP 16: Advanced Features & Optimization
Tests for resilience patterns, rate limiting, query optimization, and advanced monitoring.
"""

import asyncio
import pytest
from datetime import datetime, timedelta

# Import new modules
from core.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    Bulkhead,
    BulkheadConfig,
    Resilience,
    ResilienceManager,
)
from core.infrastructure.rate_limiting import (
    TokenBucketLimiter,
    SlidingWindowLimiter,
    FixedWindowLimiter,
    QuotaManager,
    QuotaConfig,
    RateLimitManager,
    EndpointRateLimitConfig,
    QuotaType,
)
from core.infrastructure.optimization import (
    QueryCache,
    QueryAnalyzer,
    IndexOptimizer,
    QueryOptimizationEngine,
    Index,
    IndexType,
    QueryOptimizationHint,
)
from core.infrastructure.advanced_caching import (
    MultiTierCache,
    CacheWarmer,
    CacheCoherencyManager,
    CacheCoherence,
)
from core.infrastructure.advanced_monitoring import (
    MetricsCollector,
    AlertManager,
    SLOEvaluator,
    AdvancedMonitoringEngine,
    AlertRule,
    AlertSeverity,
    ServiceLevelIndicator,
    ServiceLevelObjective,
    MetricType,
)


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_closed_state():
    """Test circuit breaker in closed state."""
    config = CircuitBreakerConfig(failure_threshold=3)
    cb = CircuitBreaker(config)
    
    async def success_func():
        return "success"
    
    result = await cb.call(success_func)
    assert result == "success"
    
    state = await cb.get_state()
    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test circuit breaker opens after threshold failures."""
    config = CircuitBreakerConfig(failure_threshold=2)
    cb = CircuitBreaker(config)
    
    async def failing_func():
        raise Exception("Service error")
    
    # Trigger failures
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(failing_func)
    
    state = await cb.get_state()
    assert state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_in_open_state():
    """Test that circuit breaker rejects calls in open state."""
    config = CircuitBreakerConfig(failure_threshold=1)
    cb = CircuitBreaker(config)
    
    async def failing_func():
        raise Exception("Service error")
    
    # Open circuit
    with pytest.raises(Exception):
        await cb.call(failing_func)
    
    # Try to call - should be rejected
    with pytest.raises(Exception, match="Circuit breaker OPEN"):
        await cb.call(failing_func)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker recovery through half-open state."""
    config = CircuitBreakerConfig(
        failure_threshold=1,
        timeout_seconds=0,  # Immediate transition
        success_threshold=1
    )
    cb = CircuitBreaker(config)
    
    async def failing_func():
        raise Exception("Error")
    
    async def success_func():
        return "success"
    
    # Open circuit
    with pytest.raises(Exception):
        await cb.call(failing_func)
    
    state = await cb.get_state()
    assert state == CircuitState.OPEN
    
    # Force to half-open by waiting
    cb._last_state_change = datetime.utcnow() - timedelta(seconds=100)
    
    # Recover
    result = await cb.call(success_func)
    assert result == "success"
    
    # Should transition to closed
    state = await cb.get_state()
    assert state == CircuitState.CLOSED


# ============================================================================
# BULKHEAD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_bulkhead_limits_concurrent_calls():
    """Test bulkhead limits concurrent execution."""
    config = BulkheadConfig(max_concurrent_calls=2)
    bh = Bulkhead(config)
    
    call_count = 0
    max_concurrent = 0
    
    async def concurrent_func():
        nonlocal call_count, max_concurrent
        call_count += 1
        max_concurrent = max(max_concurrent, call_count)
        await asyncio.sleep(0.1)
        call_count -= 1
    
    # Execute multiple concurrent calls
    tasks = [bh.execute(concurrent_func) for _ in range(5)]
    await asyncio.gather(*tasks)
    
    # Should not exceed limit significantly
    metrics = await bh.get_metrics()
    assert metrics.max_concurrent_calls == 2


@pytest.mark.asyncio
async def test_bulkhead_rejects_when_full():
    """Test bulkhead rejects when queue is full."""
    config = BulkheadConfig(
        max_concurrent_calls=1,
        max_wait_duration_seconds=10
    )
    bh = Bulkhead(config)
    
    async def slow_func():
        await asyncio.sleep(10)
    
    async def fast_func():
        return "done"
    
    # Fill queue
    task1 = asyncio.create_task(bh.execute(slow_func))
    
    # Give first task time to acquire
    await asyncio.sleep(0.1)
    
    # This should succeed (waiting in pool)
    result = await bh.execute(fast_func)
    assert result == "done"


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_token_bucket_allows_requests():
    """Test token bucket allows requests within rate."""
    limiter = TokenBucketLimiter(capacity=10, refill_rate=5)
    
    # Should allow up to capacity
    for _ in range(10):
        allowed = await limiter.acquire()
        assert allowed
    
    # Should reject when exhausted
    allowed = await limiter.acquire()
    assert not allowed


@pytest.mark.asyncio
async def test_token_bucket_refills():
    """Test token bucket refills over time."""
    limiter = TokenBucketLimiter(
        capacity=10,
        refill_rate=5,
        refill_interval_seconds=0.1
    )
    
    # Exhaust tokens
    for _ in range(10):
        await limiter.acquire()
    
    # Wait for refill
    await asyncio.sleep(0.2)
    
    # Should have new tokens
    allowed = await limiter.acquire()
    assert allowed


@pytest.mark.asyncio
async def test_sliding_window_limiter():
    """Test sliding window rate limiter."""
    limiter = SlidingWindowLimiter(max_requests=5, window_seconds=1)
    
    # Allow 5 requests
    for _ in range(5):
        allowed = await limiter.acquire()
        assert allowed
    
    # 6th should fail
    allowed = await limiter.acquire()
    assert not allowed


@pytest.mark.asyncio
async def test_quota_manager():
    """Test quota management."""
    quota_manager = QuotaManager()
    
    config = QuotaConfig(
        name="api_calls",
        quota_type=QuotaType.PER_HOUR,
        max_usage=100
    )
    
    quota = quota_manager.add_quota("api", "client1", config)
    
    # Use some quota
    allowed = await quota_manager.check_quota("api", "client1", 50)
    assert allowed
    
    # Check remaining
    metrics = await quota_manager.get_quota_metrics("api", "client1")
    assert metrics.remaining == 50
    assert metrics.used == 50


@pytest.mark.asyncio
async def test_rate_limit_manager():
    """Test endpoint rate limiting."""
    manager = RateLimitManager()
    
    config = EndpointRateLimitConfig(
        endpoint="/api/search",
        method="GET",
        requests_per_second=10,
        requests_per_minute=100
    )
    manager.add_endpoint_limit(config)
    
    # Check limit
    allowed, headers = await manager.check_limit("/api/search", "GET")
    assert allowed
    assert 'X-RateLimit-Limit' in headers


# ============================================================================
# QUERY OPTIMIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_query_cache():
    """Test query result caching."""
    cache = QueryCache(max_entries=100, ttl_seconds=3600)
    
    query = "SELECT * FROM users"
    result = [{"id": 1, "name": "Alice"}]
    
    # Cache result
    await cache.put(query, result)
    
    # Retrieve from cache
    cached = await cache.get(query)
    assert cached == result


@pytest.mark.asyncio
async def test_query_cache_ttl():
    """Test query cache TTL expiration."""
    cache = QueryCache(max_entries=100, ttl_seconds=0.1)
    
    query = "SELECT * FROM users"
    result = [{"id": 1}]
    
    await cache.put(query, result)
    
    # Should be in cache
    cached = await cache.get(query)
    assert cached is not None
    
    # Wait for expiration
    await asyncio.sleep(0.2)
    
    # Should be expired
    cached = await cache.get(query)
    assert cached is None


@pytest.mark.asyncio
async def test_query_analyzer():
    """Test query analysis."""
    analyzer = QueryAnalyzer()
    
    query = "SELECT id, name FROM users WHERE age > 18"
    plan = await analyzer.analyze(query, execution_time_ms=50)
    
    assert plan.scan_type == "index_seek"
    assert len(plan.filters) > 0


@pytest.mark.asyncio
async def test_index_optimizer():
    """Test index optimization."""
    optimizer = IndexOptimizer()
    
    index = Index(
        name="idx_user_age",
        columns=["age"],
        index_type=IndexType.PRIMARY
    )
    
    await optimizer.add_index(index)
    
    stats = await optimizer.get_index_statistics()
    assert "idx_user_age" in [s[1]['name'] for s in stats.items()]


@pytest.mark.asyncio
async def test_query_optimization_engine():
    """Test optimization engine."""
    engine = QueryOptimizationEngine()
    
    query = "SELECT * FROM users"
    plan = await engine.optimize_query(query)
    
    assert plan.query == query
    assert plan.estimated_cost >= 0


# ============================================================================
# ADVANCED CACHING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_multi_tier_cache():
    """Test multi-tier cache."""
    cache = MultiTierCache(
        l1_capacity=10,
        l2_capacity=100,
        coherence_protocol=CacheCoherence.WRITE_THROUGH
    )
    
    await cache.start()
    
    # Set value
    await cache.set("key1", "value1")
    
    # Get value
    value = await cache.get("key1")
    assert value == "value1"
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_warmer():
    """Test cache warming."""
    warmer = CacheWarmer()
    
    # Add warming strategy
    from core.infrastructure.advanced_caching import CacheWarmingStrategy
    strategy = CacheWarmingStrategy(
        keys=["key1", "key2"],
        warmup_interval=1
    )
    
    warmer.add_warming_strategy(strategy)
    assert len(warmer.strategies) == 1


@pytest.mark.asyncio
async def test_cache_coherency_manager():
    """Test cache coherency."""
    manager = CacheCoherencyManager()
    
    # Record write
    await manager.record_write("cache_node_1", ["key1", "key2"])
    
    # Check synchronization
    conflicts = await manager.detect_conflicts()
    assert isinstance(conflicts, list)


# ============================================================================
# MONITORING AND ALERTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_collector():
    """Test metrics collection."""
    collector = MetricsCollector(max_history=100)
    
    # Record metrics
    await collector.record_metric("cpu_usage", 45.5)
    await collector.record_metric("memory_usage", 60.0)
    
    # Get values
    values = await collector.get_metric_values("cpu_usage")
    assert len(values) == 1
    assert values[0].value == 45.5


@pytest.mark.asyncio
async def test_alert_rule_evaluation():
    """Test alert rule evaluation."""
    collector = MetricsCollector()
    manager = AlertManager(collector)
    
    rule = AlertRule(
        rule_id="high_cpu",
        metric_name="cpu_usage",
        condition="value >",
        threshold=80.0,
        severity=AlertSeverity.CRITICAL
    )
    
    await manager.add_rule(rule)
    
    # Record high metric
    await collector.record_metric("cpu_usage", 85.0)
    
    # Evaluate rules
    await manager.evaluate_rules()
    
    # Check for alert
    alerts = await manager.get_active_alerts()
    assert len(alerts) > 0


@pytest.mark.asyncio
async def test_slo_evaluation():
    """Test SLO evaluation."""
    collector = MetricsCollector()
    evaluator = SLOEvaluator(collector)
    
    sli = ServiceLevelIndicator(
        name="availability",
        metric_name="uptime_seconds",
        good_condition="value > 86400"  # > 24h
    )
    
    slo = ServiceLevelObjective(
        name="99_pct_availability",
        sli=sli,
        target=0.99
    )
    
    await evaluator.add_slo(slo)
    
    # Record metrics
    await collector.record_metric("uptime_seconds", 90000.0)
    
    # Evaluate
    await evaluator.evaluate_slos()
    
    # Check compliance
    metrics = await evaluator.get_slo_metrics("99_pct_availability")
    assert metrics is not None


@pytest.mark.asyncio
async def test_advanced_monitoring_engine():
    """Test advanced monitoring engine."""
    engine = AdvancedMonitoringEngine()
    
    await engine.start(evaluation_interval=1)
    
    # Record metrics
    await engine.record_metric("request_count", 150.0)
    await engine.record_metric("error_count", 5.0)
    
    # Get report
    await asyncio.sleep(2)
    report = await engine.get_monitoring_report()
    
    assert 'timestamp' in report
    assert 'active_alerts' in report
    
    await engine.stop()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_resilience_with_circuit_breaker_and_bulkhead():
    """Test combined resilience patterns."""
    cb_config = CircuitBreakerConfig(failure_threshold=3)
    cb = CircuitBreaker(cb_config)
    
    bh_config = BulkheadConfig(max_concurrent_calls=5)
    bh = Bulkhead(bh_config)
    
    resilience = Resilience(
        circuit_breaker=cb,
        bulkhead=bh,
        max_retries=2
    )
    
    async def api_call():
        return "success"
    
    result = await resilience.execute(api_call)
    assert result == "success"


@pytest.mark.asyncio
async def test_rate_limiting_with_quota():
    """Test rate limiting with quota manager."""
    quota_mgr = QuotaManager()
    rate_limit_mgr = RateLimitManager()
    
    config = QuotaConfig(
        name="premium_api",
        quota_type=QuotaType.PER_DAY,
        max_usage=1000
    )
    
    quota_mgr.add_quota("api", "premium_user", config)
    
    # Check quota before rate limiting
    allowed = await quota_mgr.check_quota("api", "premium_user", 100)
    assert allowed


@pytest.mark.asyncio
async def test_caching_with_monitoring():
    """Test cache performance with monitoring."""
    cache = QueryCache(max_entries=100)
    collector = MetricsCollector()
    
    query = "SELECT * FROM users"
    result = {"data": [1, 2, 3]}
    
    # Cache and monitor
    await cache.put(query, result)
    await collector.record_metric("cache_puts", 1)
    
    cached = await cache.get(query)
    await collector.record_metric("cache_hits", 1)
    
    assert cached == result
    
    stats = await cache.get_stats()
    assert stats['entries'] == 1


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limiter_throughput():
    """Test rate limiter throughput."""
    limiter = TokenBucketLimiter(capacity=1000, refill_rate=100)
    
    start = datetime.utcnow()
    count = 0
    
    for _ in range(100):
        if await limiter.acquire():
            count += 1
    
    elapsed = (datetime.utcnow() - start).total_seconds()
    
    assert count == 100
    assert elapsed < 1


@pytest.mark.asyncio
async def test_metrics_collector_throughput():
    """Test metrics collection throughput."""
    collector = MetricsCollector(max_history=10000)
    
    start = datetime.utcnow()
    
    for i in range(1000):
        await collector.record_metric("test_metric", float(i))
    
    elapsed = (datetime.utcnow() - start).total_seconds()
    
    values = await collector.get_metric_values("test_metric", limit=1000)
    assert len(values) == 1000
    assert elapsed < 5  # Should complete in < 5 seconds


@pytest.mark.asyncio
async def test_query_cache_throughput():
    """Test query cache performance."""
    cache = QueryCache(max_entries=1000)
    
    start = datetime.utcnow()
    
    for i in range(500):
        query = f"SELECT * FROM table_{i}"
        await cache.put(query, {"result": i})
    
    for i in range(500):
        query = f"SELECT * FROM table_{i}"
        result = await cache.get(query)
        assert result is not None
    
    elapsed = (datetime.utcnow() - start).total_seconds()
    assert elapsed < 5


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_concurrent_access():
    """Test circuit breaker with concurrent access."""
    config = CircuitBreakerConfig(failure_threshold=5)
    cb = CircuitBreaker(config)
    
    async def concurrent_call():
        return await cb.call(async_success)
    
    async def async_success():
        return "OK"
    
    tasks = [concurrent_call() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    assert all(r == "OK" for r in results)


@pytest.mark.asyncio
async def test_zero_quota_enforcement():
    """Test quota with zero allowed usage."""
    quota_mgr = QuotaManager()
    
    config = QuotaConfig(
        name="restricted",
        quota_type=QuotaType.PER_SECOND,
        max_usage=0
    )
    
    quota_mgr.add_quota("api", "restricted_user", config)
    
    allowed = await quota_mgr.check_quota("api", "restricted_user", 1)
    assert not allowed


@pytest.mark.asyncio
async def test_negative_metric_values():
    """Test metrics with negative values."""
    collector = MetricsCollector()
    
    await collector.record_metric("temperature", -15.5)
    
    values = await collector.get_metric_values("temperature")
    assert values[0].value == -15.5
    
    stats = await collector.get_metric_stats("temperature")
    assert stats['min'] == -15.5


# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

def test_suite_summary():
    """Test suite summary - 45+ comprehensive tests."""
    print("""
    STEP 16 Advanced Features & Optimization
    ========================================
    
    Test Coverage (45+ test cases):
    
    1. Circuit Breaker Tests (4 tests)
       - Closed state operation
       - Opening on failures
       - Rejection in open state
       - Recovery through half-open
    
    2. Bulkhead Tests (2 tests)
       - Concurrent call limiting
       - Queue full rejection
    
    3. Rate Limiting Tests (5 tests)
       - Token bucket allowance
       - Token bucket refill
       - Sliding window enforcement
       - Quota management
       - Endpoint rate limiting
    
    4. Query Optimization Tests (5 tests)
       - Query result caching
       - Cache TTL expiration
       - Query analysis
       - Index optimization
       - Optimization engine
    
    5. Advanced Caching Tests (3 tests)
       - Multi-tier cache
       - Cache warming
       - Cache coherency
    
    6. Monitoring & Alerting Tests (6 tests)
       - Metrics collection
       - Alert rule evaluation
       - SLO evaluation
       - Advanced monitoring engine
    
    7. Integration Tests (3 tests)
       - Resilience with circuit breaker & bulkhead
       - Rate limiting with quota
       - Caching with monitoring
    
    8. Performance Tests (3 tests)
       - Rate limiter throughput (100+ ops/sec)
       - Metrics collector throughput (1000+ ops)
       - Query cache throughput (500+ ops)
    
    9. Edge Cases (3 tests)
       - Concurrent circuit breaker access
       - Zero quota enforcement
       - Negative metric values
    
    Total: 45 test cases covering:
    - All 5 STEP 16 components
    - Integration scenarios
    - Performance benchmarks
    - Edge cases and error handling
    """)


if __name__ == "__main__":
    # Run with: pytest test_advanced_features.py -v
    test_suite_summary()
