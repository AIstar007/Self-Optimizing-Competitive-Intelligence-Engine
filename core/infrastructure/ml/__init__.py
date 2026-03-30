"""ML infrastructure initialization and singleton managers."""

import logging
from typing import Optional

from core.infrastructure.ml.pipeline import PipelineOrchestrator
from core.infrastructure.ml.predictive_models import (
    TimeSeriesForecaster,
    MarketPredictor,
    CompetitiveForecaster,
)
from core.infrastructure.ml.anomaly_detection import RealTimeAnomalyDetector
from core.infrastructure.ml.market_analysis import (
    MarketSegmentation,
    CompetitorAnalysis,
    MarketShareCalculator,
    TrendAnalyzer,
)

logger = logging.getLogger(__name__)

# Singleton instances
_pipeline_orchestrator: Optional[PipelineOrchestrator] = None
_market_predictor: Optional[MarketPredictor] = None
_competitive_forecaster: Optional[CompetitiveForecaster] = None
_anomaly_detector: Optional[RealTimeAnomalyDetector] = None
_market_segmentation: Optional[MarketSegmentation] = None
_competitor_analysis: Optional[CompetitorAnalysis] = None
_market_share_calculator: Optional[MarketShareCalculator] = None
_trend_analyzer: Optional[TrendAnalyzer] = None


def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator singleton."""
    global _pipeline_orchestrator
    if _pipeline_orchestrator is None:
        _pipeline_orchestrator = PipelineOrchestrator()
        logger.info("Initialized PipelineOrchestrator")
    return _pipeline_orchestrator


def get_market_predictor() -> MarketPredictor:
    """Get market predictor singleton."""
    global _market_predictor
    if _market_predictor is None:
        _market_predictor = MarketPredictor()
        logger.info("Initialized MarketPredictor")
    return _market_predictor


def get_competitive_forecaster() -> CompetitiveForecaster:
    """Get competitive forecaster singleton."""
    global _competitive_forecaster
    if _competitive_forecaster is None:
        _competitive_forecaster = CompetitiveForecaster()
        logger.info("Initialized CompetitiveForecaster")
    return _competitive_forecaster


def get_anomaly_detector() -> RealTimeAnomalyDetector:
    """Get anomaly detector singleton."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = RealTimeAnomalyDetector()
        logger.info("Initialized RealTimeAnomalyDetector")
    return _anomaly_detector


def get_market_segmentation() -> MarketSegmentation:
    """Get market segmentation singleton."""
    global _market_segmentation
    if _market_segmentation is None:
        _market_segmentation = MarketSegmentation()
        logger.info("Initialized MarketSegmentation")
    return _market_segmentation


def get_competitor_analysis() -> CompetitorAnalysis:
    """Get competitor analysis singleton."""
    global _competitor_analysis
    if _competitor_analysis is None:
        _competitor_analysis = CompetitorAnalysis()
        logger.info("Initialized CompetitorAnalysis")
    return _competitor_analysis


def get_market_share_calculator() -> MarketShareCalculator:
    """Get market share calculator singleton."""
    global _market_share_calculator
    if _market_share_calculator is None:
        _market_share_calculator = MarketShareCalculator()
        logger.info("Initialized MarketShareCalculator")
    return _market_share_calculator


def get_trend_analyzer() -> TrendAnalyzer:
    """Get trend analyzer singleton."""
    global _trend_analyzer
    if _trend_analyzer is None:
        _trend_analyzer = TrendAnalyzer()
        logger.info("Initialized TrendAnalyzer")
    return _trend_analyzer


__all__ = [
    "get_pipeline_orchestrator",
    "get_market_predictor",
    "get_competitive_forecaster",
    "get_anomaly_detector",
    "get_market_segmentation",
    "get_competitor_analysis",
    "get_market_share_calculator",
    "get_trend_analyzer",
]
