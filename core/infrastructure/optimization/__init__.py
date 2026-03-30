"""Query Optimization and Index Management Module

Query analysis, caching, and index optimization recommendations.
"""

from .query import (
    QueryCache,
    QueryAnalyzer,
    IndexOptimizer,
    QueryOptimizationEngine,
    Index,
    QueryPlan,
    QueryMetrics,
    IndexRecommendation,
    IndexType,
    QueryOptimizationHint,
    get_optimization_engine,
)

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
