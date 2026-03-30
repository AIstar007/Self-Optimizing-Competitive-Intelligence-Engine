"""Application use cases."""

from core.application.use_cases.base import UseCase, UseCaseResponse
from core.application.use_cases.competitive_intelligence_usecases import (
    SearchCompetitorSignalsUseCase,
    SearchCompetitorSignalsRequest,
    SearchCompetitorSignalsResponse,
    GenerateIntelligenceReportUseCase,
    GenerateIntelligenceReportRequest,
    GenerateIntelligenceReportResponse,
    AnalyzeMarketTrendsUseCase,
    AnalyzeMarketTrendsRequest,
    AnalyzeMarketTrendsResponse,
    TrackCompetitorActivityUseCase,
    TrackCompetitorActivityRequest,
    TrackCompetitorActivityResponse,
    LearnFromFeedbackUseCase,
    LearnFromFeedbackRequest,
    LearnFromFeedbackResponse,
)

__all__ = [
    # Base
    "UseCase",
    "UseCaseResponse",
    # Search Competitor Signals
    "SearchCompetitorSignalsUseCase",
    "SearchCompetitorSignalsRequest",
    "SearchCompetitorSignalsResponse",
    # Generate Intelligence Report
    "GenerateIntelligenceReportUseCase",
    "GenerateIntelligenceReportRequest",
    "GenerateIntelligenceReportResponse",
    # Analyze Market Trends
    "AnalyzeMarketTrendsUseCase",
    "AnalyzeMarketTrendsRequest",
    "AnalyzeMarketTrendsResponse",
    # Track Competitor Activity
    "TrackCompetitorActivityUseCase",
    "TrackCompetitorActivityRequest",
    "TrackCompetitorActivityResponse",
    # Learn From Feedback
    "LearnFromFeedbackUseCase",
    "LearnFromFeedbackRequest",
    "LearnFromFeedbackResponse",
]
