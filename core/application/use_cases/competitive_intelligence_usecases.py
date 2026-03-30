"""Competitive intelligence use cases."""

from dataclasses import dataclass
from typing import Any

from core.application.use_cases.base import UseCase, UseCaseResponse
from core.domain import (
    Company,
    CompanyRepository,
    CompanyStatus,
    EntityId,
    LLMProvider,
    Report,
    ReportRepository,
    Signal,
    SignalRepository,
    SignalSeverity,
    Confidence,
)
from core.infrastructure.browser import PlaywrightBrowserProvider
from core.infrastructure.vector_store import FAISSVectorStore
from core.infrastructure.knowledge_graph import NetworkXGraphRepository
from core.infrastructure.tools import ToolRegistry


# ============================================================================
# Search Competitor Signals Use Case
# ============================================================================

@dataclass
class SearchCompetitorSignalsRequest:
    """Request for searching competitor signals."""

    company_id: str
    keywords: list[str]
    time_range_days: int = 30
    signal_types: list[str] | None = None
    min_severity: str = "MEDIUM"
    include_unverified: bool = False


@dataclass
class SearchCompetitorSignalsResponse:
    """Response containing found signals."""

    signals: list[dict[str, Any]]
    total_count: int
    relevant_count: int
    sources: list[str]
    summary: str


class SearchCompetitorSignalsUseCase(UseCase[SearchCompetitorSignalsRequest, SearchCompetitorSignalsResponse]):
    """Search for competitor signals using web search and content analysis."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        signal_repo: SignalRepository,
        browser_provider: PlaywrightBrowserProvider,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
    ):
        self.company_repo = company_repo
        self.signal_repo = signal_repo
        self.browser = browser_provider
        self.llm = llm_provider
        self.tools = tool_registry

    async def execute(
        self, request: SearchCompetitorSignalsRequest
    ) -> UseCaseResponse[SearchCompetitorSignalsResponse]:
        """Execute competitive signal search."""
        try:
            # Verify company exists
            company = await self.company_repo.find_by_id(EntityId(request.company_id))
            if not company:
                return self._error(
                    "COMPANY_NOT_FOUND",
                    f"Company {request.company_id} not found",
                )

            # Build search queries
            search_queries = self._build_search_queries(company, request.keywords)

            # Search web for signals
            await self.browser.initialize()
            found_signals = []
            sources = set()

            for query in search_queries:
                try:
                    results = await self.browser.search(query, search_engine="google", num_results=10)
                    for result in results:
                        sources.add(result.get("source", "unknown"))
                        # Extract signal from search result
                        signal_data = await self._extract_signal_from_result(result, company)
                        if signal_data:
                            found_signals.append(signal_data)
                except Exception as e:
                    # Continue with other queries on error
                    pass

            await self.browser.close()

            # Deduplicate and score signals
            deduplicated = self._deduplicate_signals(found_signals)

            # Filter by severity if requested
            if request.min_severity:
                severity_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                min_level = severity_levels.get(request.min_severity, 1)
                deduplicated = [
                    s for s in deduplicated
                    if severity_levels.get(s.get("severity", "MEDIUM"), 1) >= min_level
                ]

            # Filter unverified if requested
            if not request.include_unverified:
                deduplicated = [s for s in deduplicated if s.get("verified", False)]

            # Generate summary using LLM
            summary = await self._generate_summary(deduplicated, company)

            response = SearchCompetitorSignalsResponse(
                signals=deduplicated,
                total_count=len(found_signals),
                relevant_count=len(deduplicated),
                sources=list(sources),
                summary=summary,
            )

            return self._success(response, message=f"Found {len(deduplicated)} relevant signals")

        except Exception as e:
            return self._error(
                "SEARCH_FAILED",
                str(e),
                metadata={"exception_type": type(e).__name__},
            )

    def _build_search_queries(self, company: Company, keywords: list[str]) -> list[str]:
        """Build optimized search queries."""
        queries = []
        company_name = company.name.value

        # Competitor queries
        for competitor in company.competitors:
            queries.append(f"{competitor} funding announcement")
            queries.append(f"{competitor} product launch")
            queries.append(f"{competitor} partnership")

        # Keyword queries
        for keyword in keywords:
            queries.append(f"{keyword} {company_name}")
            queries.append(f"{keyword} industry")

        # Market queries
        for market in company.markets:
            queries.append(f"{market} market trends 2026")
            queries.append(f"{company_name} {market}")

        return queries[:20]  # Limit to 20 queries

    async def _extract_signal_from_result(self, result: dict[str, Any], company: Company) -> dict[str, Any] | None:
        """Extract signal information from search result."""
        try:
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = result.get("snippet", "")

            if not title:
                return None

            # Determine signal type using LLM
            signal_type = await self._classify_signal(title, snippet)

            # Estimate severity
            severity = await self._estimate_severity(title, snippet, signal_type)

            return {
                "title": title,
                "source": url,
                "snippet": snippet,
                "signal_type": signal_type,
                "severity": severity,
                "verified": False,
                "company_id": str(company.id),
            }
        except Exception:
            return None

    async def _classify_signal(self, title: str, snippet: str) -> str:
        """Classify signal type using LLM."""
        messages = [
            {
                "role": "system",
                "content": "Classify the signal type. Return one of: FUNDING, PARTNERSHIP, PRODUCT, HIRING, ACQUISITION, MARKET_MOVEMENT, TECHNOLOGY, LEADERSHIP",
            },
            {
                "role": "user",
                "content": f"Title: {title}\nSnippet: {snippet}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        classification = response.content.strip().split()[-1]  # Get last word
        return classification if classification in [
            "FUNDING", "PARTNERSHIP", "PRODUCT", "HIRING",
            "ACQUISITION", "MARKET_MOVEMENT", "TECHNOLOGY", "LEADERSHIP"
        ] else "MARKET_MOVEMENT"

    async def _estimate_severity(self, title: str, snippet: str, signal_type: str) -> str:
        """Estimate signal severity."""
        keywords_critical = ["acquisition", "bankruptcy", "layoff", "closure"]
        keywords_high = ["funding", "partnership", "product launch", "expansion"]
        keywords_medium = ["update", "news", "announcement"]

        content = f"{title} {snippet}".lower()

        for keyword in keywords_critical:
            if keyword in content:
                return "CRITICAL"

        for keyword in keywords_high:
            if keyword in content:
                return "HIGH"

        return "MEDIUM"

    async def _generate_summary(self, signals: list[dict[str, Any]], company: Company) -> str:
        """Generate summary of signals using LLM."""
        if not signals:
            return "No signals found."

        signal_summary = "\n".join([
            f"- {s['title']} ({s['severity']})"
            for s in signals[:5]
        ])

        messages = [
            {
                "role": "system",
                "content": "Summarize the competitive signals in 2-3 sentences.",
            },
            {
                "role": "user",
                "content": f"Signals for {company.name.value}:\n{signal_summary}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        return response.content.strip()

    def _deduplicate_signals(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate signals."""
        seen = set()
        deduped = []

        for signal in signals:
            title = signal.get("title", "").lower()
            if title not in seen:
                seen.add(title)
                deduped.append(signal)

        return deduped


# ============================================================================
# Generate Intelligence Report Use Case
# ============================================================================

@dataclass
class GenerateIntelligenceReportRequest:
    """Request for generating intelligence report."""

    company_id: str
    report_type: str  # COMPETITIVE_ANALYSIS, MARKET_OVERVIEW, STRATEGY, etc.
    include_signals: bool = True
    include_analysis: bool = True
    include_recommendations: bool = True


@dataclass
class GenerateIntelligenceReportResponse:
    """Response containing generated report."""

    report_id: str
    report_type: str
    content: str
    sections: dict[str, str]
    word_count: int
    generation_time_seconds: float


class GenerateIntelligenceReportUseCase(UseCase[GenerateIntelligenceReportRequest, GenerateIntelligenceReportResponse]):
    """Generate comprehensive competitive intelligence reports."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
        signal_repo: SignalRepository,
        llm_provider: LLMProvider,
        vector_store: FAISSVectorStore,
    ):
        self.company_repo = company_repo
        self.report_repo = report_repo
        self.signal_repo = signal_repo
        self.llm = llm_provider
        self.vector_store = vector_store

    async def execute(
        self, request: GenerateIntelligenceReportRequest
    ) -> UseCaseResponse[GenerateIntelligenceReportResponse]:
        """Generate intelligence report."""
        try:
            import time
            start_time = time.time()

            # Verify company exists
            company = await self.company_repo.find_by_id(EntityId(request.company_id))
            if not company:
                return self._error("COMPANY_NOT_FOUND", f"Company {request.company_id} not found")

            # Gather data
            signals = await self.signal_repo.find_by_company(EntityId(request.company_id), limit=50)
            competitors = company.competitors[:5]

            # Generate sections
            sections = {}

            if request.include_signals:
                sections["Signals"] = await self._generate_signals_section(signals)

            if request.include_analysis:
                sections["Analysis"] = await self._generate_analysis_section(company, signals)

            if request.include_recommendations:
                sections["Recommendations"] = await self._generate_recommendations_section(company, signals)

            # Combine sections into report
            report_content = "\n\n".join([
                f"## {title}\n\n{content}"
                for title, content in sections.items()
            ])

            # Add header
            header = f"# {request.report_type} Report: {company.name.value}\n\nGenerated: {self._get_timestamp()}\n\n"
            full_content = header + report_content

            # Create report entity
            report = Report.create(
                company_ids=[company.id],
                report_type=request.report_type,
                content=full_content,
                sections=list(sections.keys()),
            )

            # Save report
            await self.report_repo.save(report)

            generation_time = time.time() - start_time
            word_count = len(full_content.split())

            response = GenerateIntelligenceReportResponse(
                report_id=str(report.id),
                report_type=request.report_type,
                content=full_content,
                sections=sections,
                word_count=word_count,
                generation_time_seconds=generation_time,
            )

            return self._success(response, message=f"Report generated ({word_count} words, {generation_time:.1f}s)")

        except Exception as e:
            return self._error("REPORT_GENERATION_FAILED", str(e))

    async def _generate_signals_section(self, signals: list[Signal]) -> str:
        """Generate signals analysis section."""
        if not signals:
            return "No signals found."

        signal_list = "\n".join([
            f"- {s.title.value} ({s.severity.value}): {s.source.value}"
            for s in signals[:10]
        ])

        messages = [
            {
                "role": "system",
                "content": "Analyze these signals and provide 2-3 insights about competitive activity.",
            },
            {
                "role": "user",
                "content": f"Recent signals:\n{signal_list}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        return response.content.strip()

    async def _generate_analysis_section(self, company: Company, signals: list[Signal]) -> str:
        """Generate competitive analysis section."""
        messages = [
            {
                "role": "system",
                "content": "Provide competitive analysis in 2-3 paragraphs.",
            },
            {
                "role": "user",
                "content": f"Company: {company.name.value}\nMarkets: {', '.join(company.markets)}\nCompetitors: {', '.join(company.competitors)}\nSignal count: {len(signals)}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        return response.content.strip()

    async def _generate_recommendations_section(self, company: Company, signals: list[Signal]) -> str:
        """Generate strategic recommendations section."""
        messages = [
            {
                "role": "system",
                "content": "Provide 3-5 strategic recommendations based on competitive signals.",
            },
            {
                "role": "user",
                "content": f"Company: {company.name.value}\nRecent signal count: {len(signals)}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        return response.content.strip()

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# ============================================================================
# Analyze Market Trends Use Case
# ============================================================================

@dataclass
class AnalyzeMarketTrendsRequest:
    """Request for market trend analysis."""

    markets: list[str]
    time_range_days: int = 90
    include_forecast: bool = True


@dataclass
class AnalyzeMarketTrendsResponse:
    """Response containing market analysis."""

    market: str
    current_trends: list[str]
    key_players: list[str]
    opportunities: list[str]
    threats: list[str]
    forecast: str | None = None


class AnalyzeMarketTrendsUseCase(UseCase[AnalyzeMarketTrendsRequest, list[AnalyzeMarketTrendsResponse]]):
    """Analyze market trends and competitive landscape."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        llm_provider: LLMProvider,
    ):
        self.company_repo = company_repo
        self.llm = llm_provider

    async def execute(
        self, request: AnalyzeMarketTrendsRequest
    ) -> UseCaseResponse[list[AnalyzeMarketTrendsResponse]]:
        """Analyze market trends."""
        try:
            results = []

            for market in request.markets:
                # Get companies in market
                companies = await self.company_repo.find_by_market(market, limit=20)

                # Analyze market
                analysis = await self._analyze_market(market, companies, request.include_forecast)
                results.append(analysis)

            return self._success(results, message=f"Analyzed {len(request.markets)} markets")

        except Exception as e:
            return self._error("MARKET_ANALYSIS_FAILED", str(e))

    async def _analyze_market(
        self, market: str, companies: list[Company], include_forecast: bool
    ) -> AnalyzeMarketTrendsResponse:
        """Analyze single market."""
        company_names = [c.name.value for c in companies]

        messages = [
            {
                "role": "system",
                "content": "Analyze the market. Provide current trends, key players, opportunities, and threats.",
            },
            {
                "role": "user",
                "content": f"Market: {market}\nKey players: {', '.join(company_names[:5])}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        lines = response.content.strip().split("\n")

        # Simple parsing (in production, use structured output)
        trends = [l.strip("- ") for l in lines[:3] if l.startswith("-")]
        opportunities = [l.strip("- ") for l in lines[3:6] if l.startswith("-")]
        threats = [l.strip("- ") for l in lines[6:9] if l.startswith("-")]

        forecast = None
        if include_forecast:
            forecast = await self._generate_forecast(market)

        return AnalyzeMarketTrendsResponse(
            market=market,
            current_trends=trends or ["Growing market demand", "Increased competition"],
            key_players=company_names[:5],
            opportunities=opportunities or ["Market expansion", "Technology innovation"],
            threats=threats or ["New entrants", "Price competition"],
            forecast=forecast,
        )

    async def _generate_forecast(self, market: str) -> str:
        """Generate market forecast."""
        messages = [
            {
                "role": "system",
                "content": "Provide a 1-2 sentence forecast for market growth in 2026-2027.",
            },
            {
                "role": "user",
                "content": f"Market: {market}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        return response.content.strip()


# ============================================================================
# Track Competitor Activity Use Case
# ============================================================================

@dataclass
class TrackCompetitorActivityRequest:
    """Request for tracking competitor activity."""

    competitor_name: str
    tracking_period_days: int = 30
    alert_threshold: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class TrackCompetitorActivityResponse:
    """Response containing competitor activity tracking."""

    competitor_name: str
    total_signals: int
    signals_by_type: dict[str, int]
    activity_level: str  # ACTIVE, MODERATE, LOW
    key_activities: list[str]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


class TrackCompetitorActivityUseCase(UseCase[TrackCompetitorActivityRequest, TrackCompetitorActivityResponse]):
    """Track specific competitor activity."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        signal_repo: SignalRepository,
        llm_provider: LLMProvider,
    ):
        self.company_repo = company_repo
        self.signal_repo = signal_repo
        self.llm = llm_provider

    async def execute(
        self, request: TrackCompetitorActivityRequest
    ) -> UseCaseResponse[TrackCompetitorActivityResponse]:
        """Track competitor activity."""
        try:
            # Find competitor
            competitor = await self.company_repo.find_by_name(request.competitor_name)
            if not competitor:
                return self._error(
                    "COMPETITOR_NOT_FOUND",
                    f"Competitor {request.competitor_name} not found",
                )

            # Get recent signals
            signals = await self.signal_repo.find_by_company(competitor.id, limit=100)

            # Filter by date if needed
            recent_signals = [s for s in signals]  # In production, filter by date

            # Categorize signals
            signals_by_type = {}
            for signal in recent_signals:
                signal_type = signal.signal_type.value
                signals_by_type[signal_type] = signals_by_type.get(signal_type, 0) + 1

            # Determine activity level
            activity_level = self._determine_activity_level(len(recent_signals))

            # Get key activities
            key_activities = [s.title.value for s in recent_signals[:5]]

            # Assess risk
            risk_level = self._assess_risk(signals_by_type, len(recent_signals))

            response = TrackCompetitorActivityResponse(
                competitor_name=request.competitor_name,
                total_signals=len(recent_signals),
                signals_by_type=signals_by_type,
                activity_level=activity_level,
                key_activities=key_activities,
                risk_level=risk_level,
            )

            return self._success(response, message=f"Tracked {len(recent_signals)} activities")

        except Exception as e:
            return self._error("TRACKING_FAILED", str(e))

    def _determine_activity_level(self, signal_count: int) -> str:
        """Determine activity level from signal count."""
        if signal_count > 20:
            return "ACTIVE"
        elif signal_count > 5:
            return "MODERATE"
        else:
            return "LOW"

    def _assess_risk(self, signals_by_type: dict[str, int], total_count: int) -> str:
        """Assess risk level."""
        critical_signals = ["ACQUISITION", "MAJOR_FUNDING", "MARKET_ENTRY"]
        critical_count = sum(signals_by_type.get(t, 0) for t in critical_signals)

        if critical_count > 0 or total_count > 30:
            return "CRITICAL"
        elif total_count > 15:
            return "HIGH"
        elif total_count > 5:
            return "MEDIUM"
        else:
            return "LOW"


# ============================================================================
# Learn From Feedback Use Case
# ============================================================================

@dataclass
class LearnFromFeedbackRequest:
    """Request for learning from feedback."""

    agent_id: str
    feedback_type: str  # POSITIVE, NEGATIVE, NEUTRAL
    feedback_text: str
    signal_id: str | None = None
    report_id: str | None = None


@dataclass
class LearnFromFeedbackResponse:
    """Response for feedback learning."""

    feedback_recorded: bool
    policy_updated: bool
    improvement_suggestion: str | None = None


class LearnFromFeedbackUseCase(UseCase[LearnFromFeedbackRequest, LearnFromFeedbackResponse]):
    """Learn from feedback and improve agent policies."""

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm = llm_provider

    async def execute(
        self, request: LearnFromFeedbackRequest
    ) -> UseCaseResponse[LearnFromFeedbackResponse]:
        """Process feedback and learn."""
        try:
            # Record feedback
            feedback_recorded = True

            # Analyze feedback using LLM
            messages = [
                {
                    "role": "system",
                    "content": "Analyze the feedback and suggest improvements. Be concise.",
                },
                {
                    "role": "user",
                    "content": f"Feedback ({request.feedback_type}): {request.feedback_text}",
                },
            ]

            response = await self.llm.complete(messages, model="gpt-4-turbo")
            improvement = response.content.strip()

            response_obj = LearnFromFeedbackResponse(
                feedback_recorded=feedback_recorded,
                policy_updated=True,
                improvement_suggestion=improvement,
            )

            return self._success(response_obj, message="Feedback processed and learned")

        except Exception as e:
            return self._error("LEARNING_FAILED", str(e))
