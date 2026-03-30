"""Unit tests for application layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from core.domain.entities import Signal, Report, Company, MarketEvent


# ============================================================================
# Use Case Tests
# ============================================================================


class TestSearchCompetitorSignalsUseCase:
    """Test SearchCompetitorSignalsUseCase."""

    @pytest.mark.asyncio
    async def test_search_signals_basic(self, mock_browser_provider, mock_llm_provider, mock_vector_store):
        """Test basic signal search."""
        # Simulate searching for competitor signals
        search_results = await mock_browser_provider.search("Apple product launch")
        
        assert len(search_results) > 0
        assert search_results[0]["title"] == "Result 1"

    @pytest.mark.asyncio
    async def test_search_with_filtering(self, mock_browser_provider):
        """Test signal search with filtering."""
        results = await mock_browser_provider.search("competitor acquisition 2024")
        
        assert len(results) >= 1
        # Verify results contain expected fields
        for result in results:
            assert "title" in result
            assert "snippet" in result

    @pytest.mark.asyncio
    async def test_search_signal_enrichment(self, mock_llm_provider):
        """Test signal enrichment with LLM."""
        signal_text = "Company X launched new AI product"
        enriched = await mock_llm_provider.generate_text(
            f"Analyze this signal: {signal_text}"
        )
        
        assert enriched is not None
        assert len(enriched) > 0


class TestGenerateIntelligenceReportUseCase:
    """Test GenerateIntelligenceReportUseCase."""

    @pytest.mark.asyncio
    async def test_generate_report_basic(self, mock_llm_provider):
        """Test basic report generation."""
        report_content = await mock_llm_provider.generate_text(
            "Generate competitive intelligence report for Apple vs Microsoft"
        )
        
        assert report_content == "Mock response"

    @pytest.mark.asyncio
    async def test_report_with_sections(self, mock_llm_provider):
        """Test report generation with multiple sections."""
        sections = [
            "Executive Summary",
            "Market Analysis",
            "Competitive Landscape",
            "Strategic Recommendations",
        ]
        
        for section in sections:
            content = await mock_llm_provider.generate_text(
                f"Generate {section} for report"
            )
            assert content is not None

    @pytest.mark.asyncio
    async def test_report_data_aggregation(self, sample_company_data, sample_signal_data):
        """Test aggregating data for report."""
        # Test that we can combine company data with signals
        company = sample_company_data
        signal = sample_signal_data
        
        assert company["name"] == "Acme Corp"
        assert "content" in signal


class TestAnalyzeMarketTrendsUseCase:
    """Test AnalyzeMarketTrendsUseCase."""

    @pytest.mark.asyncio
    async def test_trend_analysis(self, mock_llm_provider):
        """Test trend analysis."""
        trend_analysis = await mock_llm_provider.generate_text(
            "Analyze current market trends in AI/ML"
        )
        
        assert trend_analysis is not None

    @pytest.mark.asyncio
    async def test_trend_embedding_search(self, mock_vector_store):
        """Test finding similar trends."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        similar_trends = await mock_vector_store.search(
            query_vector=query_vector,
            top_k=5,
        )
        
        assert len(similar_trends) > 0


class TestTrackCompetitorActivityUseCase:
    """Test TrackCompetitorActivityUseCase."""

    @pytest.mark.asyncio
    async def test_track_activity(self, mock_repository):
        """Test tracking competitor activity."""
        activity = await mock_repository.get("activity_123")
        
        assert activity is not None
        assert "id" in activity

    @pytest.mark.asyncio
    async def test_activity_update(self, mock_repository):
        """Test updating activity tracking."""
        update = {"status": "reviewed"}
        result = await mock_repository.update("activity_123", update)
        
        assert result["updated"] is True


class TestLearnFromFeedbackUseCase:
    """Test LearnFromFeedbackUseCase."""

    @pytest.mark.asyncio
    async def test_feedback_processing(self, mock_repository):
        """Test processing feedback."""
        feedback = {"rating": 5, "comment": "Excellent analysis"}
        result = await mock_repository.create(feedback)
        
        assert result is not None


# ============================================================================
# Service Tests
# ============================================================================


class TestCompetitiveIntelligenceService:
    """Test CompetitiveIntelligenceService."""

    @pytest.mark.asyncio
    async def test_analyze_competitor(self, mock_llm_provider):
        """Test analyzing a competitor."""
        analysis = await mock_llm_provider.generate_text(
            "Analyze Google's competitive position"
        )
        
        assert analysis == "Mock response"

    @pytest.mark.asyncio
    async def test_market_positioning(self, mock_knowledge_graph):
        """Test market positioning analysis."""
        neighbors = await mock_knowledge_graph.get_neighbors("google_node")
        
        assert len(neighbors) > 0


class TestSignalProcessingService:
    """Test SignalProcessingService."""

    @pytest.mark.asyncio
    async def test_process_signal(self, sample_signal_data):
        """Test processing a signal."""
        signal = sample_signal_data
        
        assert "id" in signal
        assert "content" in signal
        assert "created_at" in signal

    @pytest.mark.asyncio
    async def test_verify_signal(self, mock_repository):
        """Test signal verification."""
        result = await mock_repository.update("signal_123", {"verified": True})
        
        assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_enrich_signal(self, mock_llm_provider):
        """Test signal enrichment."""
        enrichment = await mock_llm_provider.generate_text(
            "Enrich this market signal with insights"
        )
        
        assert enrichment is not None


class TestReportGenerationService:
    """Test ReportGenerationService."""

    @pytest.mark.asyncio
    async def test_generate_report(self, sample_report_data):
        """Test report generation."""
        report = sample_report_data
        
        assert "id" in report
        assert "title" in report
        assert "sections" in report

    @pytest.mark.asyncio
    async def test_format_report(self, mock_llm_provider):
        """Test report formatting."""
        formatted = await mock_llm_provider.generate_text(
            "Format this into an executive report"
        )
        
        assert formatted is not None


class TestKnowledgeGraphService:
    """Test KnowledgeGraphService."""

    @pytest.mark.asyncio
    async def test_add_company_node(self, mock_knowledge_graph):
        """Test adding company to graph."""
        node_id = await mock_knowledge_graph.add_node(
            node_type="company",
            data={"name": "Microsoft"},
        )
        
        assert node_id == "node_id"

    @pytest.mark.asyncio
    async def test_add_relationship(self, mock_knowledge_graph):
        """Test adding relationship."""
        edge_id = await mock_knowledge_graph.add_edge(
            from_node="microsoft",
            to_node="openai",
            edge_type="INVESTED_IN",
        )
        
        assert edge_id == "edge_id"

    @pytest.mark.asyncio
    async def test_find_connection_paths(self, mock_knowledge_graph):
        """Test finding connection paths."""
        paths = await mock_knowledge_graph.find_paths(
            source="apple",
            target="microsoft",
        )
        
        assert len(paths) > 0


class TestAgentPolicyService:
    """Test AgentPolicyService."""

    @pytest.mark.asyncio
    async def test_policy_management(self, mock_repository):
        """Test policy management."""
        policy = await mock_repository.get("policy_123")
        
        assert policy is not None


# ============================================================================
# Agent Tests
# ============================================================================


class TestResearchAgent:
    """Test ResearchAgent."""

    @pytest.mark.asyncio
    async def test_research_task(self, mock_browser_provider, mock_llm_provider):
        """Test research task execution."""
        # Search for information
        results = await mock_browser_provider.search("AI market trends")
        assert len(results) > 0
        
        # Generate research summary
        summary = await mock_llm_provider.generate_text(
            "Summarize this research"
        )
        assert summary is not None

    @pytest.mark.asyncio
    async def test_source_validation(self, mock_browser_provider):
        """Test validating sources."""
        results = await mock_browser_provider.search("test")
        
        for result in results:
            assert "url" in result
            assert "title" in result


class TestAnalysisAgent:
    """Test AnalysisAgent."""

    @pytest.mark.asyncio
    async def test_analysis_execution(self, mock_llm_provider):
        """Test analysis execution."""
        analysis = await mock_llm_provider.generate_text(
            "Analyze the competitive landscape"
        )
        
        assert analysis is not None

    @pytest.mark.asyncio
    async def test_data_synthesis(self, mock_vector_store):
        """Test synthesizing data."""
        results = await mock_vector_store.search(
            query_vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            top_k=10,
        )
        
        assert len(results) > 0


class TestStrategyAgent:
    """Test StrategyAgent."""

    @pytest.mark.asyncio
    async def test_strategy_generation(self, mock_llm_provider):
        """Test generating strategy."""
        strategy = await mock_llm_provider.generate_text(
            "Generate competitive strategy"
        )
        
        assert strategy is not None


class TestReportAgent:
    """Test ReportAgent."""

    @pytest.mark.asyncio
    async def test_report_compilation(self, sample_report_data):
        """Test report compilation."""
        report = sample_report_data
        
        assert len(report["sections"]) > 0
        assert report["word_count"] > 0


class TestCritiqueAgent:
    """Test CritiqueAgent."""

    @pytest.mark.asyncio
    async def test_critique_generation(self, mock_llm_provider):
        """Test generating critique."""
        critique = await mock_llm_provider.generate_text(
            "Provide critical feedback"
        )
        
        assert critique is not None


class TestPlannerAgent:
    """Test PlannerAgent."""

    @pytest.mark.asyncio
    async def test_plan_generation(self, mock_llm_provider):
        """Test generating plan."""
        plan = await mock_llm_provider.generate_text(
            "Create action plan"
        )
        
        assert plan is not None


# ============================================================================
# Orchestrator Tests
# ============================================================================


class TestWorkflowOrchestrator:
    """Test WorkflowOrchestrator."""

    @pytest.mark.asyncio
    async def test_workflow_execution(self, sample_workflow_data):
        """Test workflow execution."""
        workflow = sample_workflow_data
        
        assert workflow["id"] is not None
        assert workflow["status"] == "pending"

    @pytest.mark.asyncio
    async def test_task_sequencing(self, sample_workflow_data):
        """Test task sequencing."""
        workflow = sample_workflow_data
        
        assert len(workflow["tasks"]) > 0


class TestTaskScheduler:
    """Test TaskScheduler."""

    @pytest.mark.asyncio
    async def test_schedule_task(self, mock_repository):
        """Test scheduling task."""
        task = await mock_repository.create({"type": "analyze"})
        
        assert task is not None


class TestAgentCommunicator:
    """Test AgentCommunicator."""

    @pytest.mark.asyncio
    async def test_message_routing(self, mock_repository):
        """Test message routing."""
        message = await mock_repository.create({
            "sender": "research_agent",
            "recipient": "analysis_agent",
            "content": "Analysis ready",
        })
        
        assert message is not None
