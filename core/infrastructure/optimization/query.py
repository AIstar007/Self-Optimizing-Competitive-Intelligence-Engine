"""
Query Optimization and Index Management Module
Analyzes queries, recommends indexes, and optimizes execution.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from threading import Lock
import json

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Index types."""
    PRIMARY = "primary"
    UNIQUE = "unique"
    COMPOSITE = "composite"
    FULL_TEXT = "full_text"
    SPATIAL = "spatial"
    BITMAP = "bitmap"


class QueryOptimizationHint(Enum):
    """Query optimization hints."""
    USE_INDEX = "use_index"
    AVOID_FULL_SCAN = "avoid_full_scan"
    ADD_INDEX = "add_index"
    REWRITE_QUERY = "rewrite_query"
    CACHE_RESULT = "cache_result"
    DENORMALIZE = "denormalize"


@dataclass
class Index:
    """Database index."""
    name: str
    columns: List[str]
    index_type: IndexType = IndexType.PRIMARY
    created_at: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    cardinality: int = 0
    enabled: bool = True
    
    def __hash__(self) -> int:
        return hash(f"{self.name}:{':'.join(self.columns)}")


@dataclass
class QueryPlan:
    """Query execution plan."""
    query: str
    estimated_cost: float = 0.0
    estimated_rows: int = 0
    scan_type: str = "full_scan"  # full_scan, index_scan, index_seek
    filters: List[str] = field(default_factory=list)
    joins: List[str] = field(default_factory=list)
    indexes_used: List[str] = field(default_factory=list)
    optimization_hints: List[QueryOptimizationHint] = field(default_factory=list)


@dataclass
class QueryMetrics:
    """Query execution metrics."""
    query: str
    execution_time_ms: float = 0.0
    rows_affected: int = 0
    cached: bool = False
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    compiled_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IndexRecommendation:
    """Index recommendation."""
    columns: List[str]
    index_type: IndexType = IndexType.COMPOSITE
    expected_improvement: float = 0.0  # percentage
    estimated_size_kb: int = 0
    priority: int = 1  # 1-5, higher = more important
    reason: str = ""


class QueryCache:
    """Caches parsed queries and execution plans."""
    
    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 3600):
        """Initialize query cache."""
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_count: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, query: str) -> Optional[Any]:
        """Get cached query result."""
        async with self._lock:
            if query in self._cache:
                result, timestamp = self._cache[query]
                
                # Check TTL
                if time.time() - timestamp < self.ttl_seconds:
                    self._access_count[query] = self._access_count.get(query, 0) + 1
                    return result
                else:
                    del self._cache[query]
                    del self._access_count[query]
            
            return None
    
    async def put(self, query: str, result: Any) -> None:
        """Cache query result."""
        async with self._lock:
            # Evict least used if at capacity
            if len(self._cache) >= self.max_entries:
                lru_query = min(
                    self._access_count.keys(),
                    key=lambda q: self._access_count.get(q, 0)
                )
                del self._cache[lru_query]
                del self._access_count[lru_query]
            
            self._cache[query] = (result, time.time())
            self._access_count[query] = 0
    
    async def invalidate(self, pattern: str = "*") -> None:
        """Invalidate cache entries."""
        async with self._lock:
            if pattern == "*":
                self._cache.clear()
                self._access_count.clear()
            else:
                # Simple pattern matching
                matching = [q for q in self._cache.keys() if pattern in q]
                for q in matching:
                    del self._cache[q]
                    del self._access_count[q]
    
    async def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        async with self._lock:
            return {
                'entries': len(self._cache),
                'total_accesses': sum(self._access_count.values())
            }


class QueryAnalyzer:
    """Analyzes query performance."""
    
    def __init__(self):
        """Initialize query analyzer."""
        self.query_history: List[QueryMetrics] = []
        self.slow_queries: List[QueryMetrics] = []
        self.slow_query_threshold_ms = 1000.0
        self._lock = asyncio.Lock()
    
    async def analyze(self, query: str, execution_time_ms: float, rows_affected: int = 0) -> QueryPlan:
        """Analyze query and return execution plan."""
        plan = QueryPlan(query=query)
        
        # Simple pattern analysis
        upper_query = query.upper()
        
        # Detect full table scan
        if "SELECT *" in upper_query and "WHERE" not in upper_query:
            plan.scan_type = "full_scan"
            plan.optimization_hints.append(QueryOptimizationHint.AVOID_FULL_SCAN)
        
        # Detect joins
        if "JOIN" in upper_query:
            plan.joins = self._extract_joins(query)
        
        # Detect filters
        if "WHERE" in upper_query:
            plan.filters = self._extract_filters(query)
            plan.scan_type = "index_seek"
        
        # Record metrics
        metrics = QueryMetrics(
            query=query,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected
        )
        
        async with self._lock:
            self.query_history.append(metrics)
            
            if execution_time_ms > self.slow_query_threshold_ms:
                self.slow_queries.append(metrics)
                logger.warning(f"Slow query detected: {query} ({execution_time_ms}ms)")
        
        return plan
    
    def _extract_joins(self, query: str) -> List[str]:
        """Extract JOIN clauses."""
        joins = []
        parts = query.split("JOIN")
        for i, part in enumerate(parts[1:], 1):
            join_table = part.split()[0]
            joins.append(join_table)
        return joins
    
    def _extract_filters(self, query: str) -> List[str]:
        """Extract WHERE filters."""
        filters = []
        if "WHERE" in query:
            where_part = query.split("WHERE")[1].split("GROUP")[0].split("ORDER")[0]
            conditions = [c.strip() for c in where_part.split("AND")]
            filters.extend(conditions)
        return filters
    
    async def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get slowest queries."""
        async with self._lock:
            sorted_queries = sorted(
                self.query_history,
                key=lambda q: q.execution_time_ms,
                reverse=True
            )
            return sorted_queries[:limit]
    
    async def clear_history(self) -> None:
        """Clear query history."""
        async with self._lock:
            self.query_history.clear()
            self.slow_queries.clear()


class IndexOptimizer:
    """Recommends and manages database indexes."""
    
    def __init__(self):
        """Initialize index optimizer."""
        self.indexes: Dict[str, Index] = {}
        self.recommendations: Dict[str, IndexRecommendation] = {}
        self._lock = asyncio.Lock()
    
    async def add_index(self, index: Index) -> None:
        """Add index to system."""
        async with self._lock:
            key = f"{index.name}:{':'.join(index.columns)}"
            self.indexes[key] = index
            logger.info(f"Index added: {key}")
    
    async def recommend_indexes(
        self,
        query_plans: List[QueryPlan],
        cardinality_data: Dict[str, int]
    ) -> List[IndexRecommendation]:
        """Recommend indexes based on query patterns."""
        recommendations = []
        
        # Analyze filter patterns
        filter_patterns: Dict[str, int] = {}
        
        for plan in query_plans:
            for filter_clause in plan.filters:
                columns = self._extract_columns(filter_clause)
                key = ':'.join(columns)
                filter_patterns[key] = filter_patterns.get(key, 0) + 1
        
        # Generate recommendations
        for columns_key, frequency in filter_patterns.items():
            if frequency > 5:  # Threshold
                columns = columns_key.split(':')
                
                # Calculate improvement
                estimated_improvement = frequency * 10.0  # percentage
                
                recommendation = IndexRecommendation(
                    columns=columns,
                    expected_improvement=estimated_improvement,
                    priority=min(5, max(1, frequency // 2)),
                    reason=f"Used in {frequency} queries"
                )
                
                recommendations.append(recommendation)
        
        async with self._lock:
            for rec in recommendations:
                key = f"rec_{':'.join(rec.columns)}"
                self.recommendations[key] = rec
        
        return recommendations
    
    def _extract_columns(self, filter_clause: str) -> List[str]:
        """Extract column names from filter."""
        columns = []
        parts = filter_clause.split("=")
        if parts:
            col = parts[0].strip().split()[-1]
            columns.append(col)
        return columns
    
    async def get_index_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get index statistics."""
        async with self._lock:
            stats = {}
            for key, index in self.indexes.items():
                stats[key] = {
                    'name': index.name,
                    'columns': index.columns,
                    'type': index.index_type.value,
                    'size_bytes': index.size_bytes,
                    'cardinality': index.cardinality,
                    'enabled': index.enabled
                }
            return stats
    
    async def remove_unused_indexes(self, usage_threshold: int = 0) -> List[str]:
        """Remove indexes below usage threshold."""
        removed = []
        async with self._lock:
            to_remove = [k for k, v in self.indexes.items() if v.cardinality < usage_threshold]
            for key in to_remove:
                del self.indexes[key]
                removed.append(key)
        return removed


class QueryOptimizationEngine:
    """Main query optimization engine."""
    
    def __init__(self):
        """Initialize optimization engine."""
        self.cache = QueryCache()
        self.analyzer = QueryAnalyzer()
        self.index_optimizer = IndexOptimizer()
        self.optimization_rules: List[Dict[str, Any]] = []
        self._lock = Lock()
    
    async def optimize_query(self, query: str) -> QueryPlan:
        """Optimize query execution."""
        # Check cache
        cached_plan = await self.cache.get(f"plan:{query}")
        if cached_plan:
            return cached_plan
        
        # Basic cost calculation
        plan = QueryPlan(query=query)
        
        # Analyze query structure
        upper_q = query.upper()
        
        if "SELECT *" in upper_q:
            plan.scan_type = "full_scan"
            plan.estimated_cost = 1000.0
        else:
            plan.scan_type = "index_seek"
            plan.estimated_cost = 10.0
        
        # Cache the plan
        await self.cache.put(f"plan:{query}", plan)
        
        return plan
    
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        slow_queries = await self.analyzer.get_slow_queries(5)
        index_stats = await self.index_optimizer.get_index_statistics()
        cache_stats = await self.cache.get_stats()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'slow_queries': len(slow_queries),
            'indexes': len(index_stats),
            'cache_entries': cache_stats['entries'],
            'total_queries_analyzed': len(self.analyzer.query_history)
        }


_optimization_engine: Optional[QueryOptimizationEngine] = None
_optimization_lock = Lock()


async def get_optimization_engine() -> QueryOptimizationEngine:
    """Get or create query optimization engine."""
    global _optimization_engine
    
    if _optimization_engine is None:
        with _optimization_lock:
            if _optimization_engine is None:
                _optimization_engine = QueryOptimizationEngine()
    
    return _optimization_engine


__all__ = [
    "QueryCache",
    "QueryAnalyzer",
    "IndexOptimizer",
    "QueryOptimizationEngine",
    "Index",
    "QueryPlan",
    "QueryMetrics",
    "IndexRecommendation",
    "IndexType",
    "QueryOptimizationHint",
    "get_optimization_engine",
]
