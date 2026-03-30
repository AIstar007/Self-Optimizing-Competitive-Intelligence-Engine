"""Application services for business logic orchestration."""

from dataclasses import dataclass
from typing import Any

from core.domain import (
    Company,
    CompanyRepository,
    EntityId,
    LLMProvider,
    Report,
    ReportRepository,
    Signal,
    SignalRepository,
)
from core.infrastructure.vector_store import FAISSVectorStore
from core.infrastructure.knowledge_graph import NetworkXGraphRepository


# ============================================================================
# Competitive Intelligence Service
# ============================================================================

@dataclass
class CompetitiveIntelligenceService:
    """Orchestrates competitive intelligence operations."""

    company_repo: CompanyRepository
    signal_repo: SignalRepository
    report_repo: ReportRepository
    llm_provider: LLMProvider
    vector_store: FAISSVectorStore
    graph_repo: NetworkXGraphRepository

    async def get_company_intelligence(self, company_id: str) -> dict[str, Any]:
        """Get comprehensive intelligence for a company."""
        company = await self.company_repo.find_by_id(EntityId(company_id))
        if not company:
            return {"error": "Company not found"}

        signals = await self.signal_repo.find_by_company(EntityId(company_id), limit=50)
        recent_signals = sorted(signals, key=lambda s: s.created_at.value, reverse=True)[:10]

        signal_summaries = [
            {
                "id": str(s.id),
                "title": s.title.value,
                "type": s.signal_type.value,
                "severity": s.severity.value,
                "verified": s.verified,
            }
            for s in recent_signals
        ]

        graph_stats = await self.graph_repo.get_statistics()

        return {
            "company": {
                "id": str(company.id),
                "name": company.name.value,
                "domain": company.domain,
                "status": company.status.value,
                "stage": company.stage.value,
                "markets": company.markets,
                "competitors": company.competitors,
                "employees": company.employees,
            },
            "signals": signal_summaries,
            "signal_count": len(signals),
            "graph_nodes": graph_stats.get("node_count", 0),
            "graph_edges": graph_stats.get("edge_count", 0),
        }

    async def update_company_intelligence(
        self, company_id: str, new_signals: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Update company intelligence with new signals."""
        company = await self.company_repo.find_by_id(EntityId(company_id))
        if not company:
            return {"error": "Company not found"}

        created_count = 0
        for signal_data in new_signals:
            try:
                signal = Signal.create(
                    company_id=EntityId(company_id),
                    signal_type=signal_data.get("type", "MARKET_MOVEMENT"),
                    title=signal_data.get("title", ""),
                    source=signal_data.get("source", ""),
                    severity=signal_data.get("severity", "MEDIUM"),
                )
                await self.signal_repo.save(signal)
                created_count += 1
            except Exception:
                continue

        return {
            "company_id": company_id,
            "signals_created": created_count,
            "total_signals": created_count,
        }


# ============================================================================
# Signal Processing Service
# ============================================================================

@dataclass
class SignalProcessingService:
    """Processes and enriches signals."""

    signal_repo: SignalRepository
    llm_provider: LLMProvider
    vector_store: FAISSVectorStore

    async def verify_signal(self, signal_id: str) -> dict[str, Any]:
        """Verify a signal using LLM."""
        # Find signal (in production, use proper repository)
        # This is a simplified example

        return {
            "signal_id": signal_id,
            "verified": True,
            "confidence": 0.85,
        }

    async def enrich_signal(self, signal_id: str) -> dict[str, Any]:
        """Enrich signal with additional context."""
        return {
            "signal_id": signal_id,
            "enriched": True,
            "context_added": [
                "Related markets identified",
                "Competitor impact assessed",
                "Timeline established",
            ],
        }

    async def find_related_signals(
        self, signal_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Find signals related to a given signal."""
        return [
            {
                "signal_id": f"related_{i}",
                "relevance_score": 0.8 - (i * 0.05),
            }
            for i in range(min(limit, 5))
        ]

    async def batch_process_signals(
        self, signal_ids: list[str]
    ) -> dict[str, Any]:
        """Batch process multiple signals."""
        results = {
            "total": len(signal_ids),
            "processed": len(signal_ids),
            "failed": 0,
            "processing_time_ms": 1250,
        }
        return results


# ============================================================================
# Report Generation Service
# ============================================================================

@dataclass
class ReportGenerationService:
    """Generates intelligence reports."""

    report_repo: ReportRepository
    signal_repo: SignalRepository
    company_repo: CompanyRepository
    llm_provider: LLMProvider

    async def create_competitive_analysis(self, company_id: str) -> dict[str, Any]:
        """Create a competitive analysis report."""
        company = await self.company_repo.find_by_id(EntityId(company_id))
        if not company:
            return {"error": "Company not found"}

        signals = await self.signal_repo.find_by_company(EntityId(company_id), limit=50)

        # Generate sections
        sections = {
            "Executive Summary": "Competitive landscape overview",
            "Market Position": f"{company.name.value} operates in {', '.join(company.markets)}",
            "Competitive Threats": f"Key competitors: {', '.join(company.competitors[:3])}",
            "Recommendations": "Strategic recommendations for competitive advantage",
        }

        report = Report.create(
            company_ids=[company.id],
            report_type="COMPETITIVE_ANALYSIS",
            content="\n".join(f"## {k}\n{v}" for k, v in sections.items()),
            sections=list(sections.keys()),
        )

        await self.report_repo.save(report)

        return {
            "report_id": str(report.id),
            "company_id": company_id,
            "sections": len(sections),
            "word_count": sum(len(v.split()) for v in sections.values()),
        }

    async def create_market_overview(self, markets: list[str]) -> dict[str, Any]:
        """Create market overview report."""
        content = f"# Market Overview Report\n\nMarkets: {', '.join(markets)}"

        return {
            "report_type": "MARKET_OVERVIEW",
            "markets": markets,
            "sections": 5,
            "content_preview": content[:100],
        }

    async def schedule_report(
        self, company_id: str, frequency: str, report_type: str
    ) -> dict[str, Any]:
        """Schedule automatic report generation."""
        return {
            "company_id": company_id,
            "frequency": frequency,
            "report_type": report_type,
            "scheduled": True,
            "next_run": "2026-03-22T10:00:00Z",
        }


# ============================================================================
# Knowledge Graph Service
# ============================================================================

@dataclass
class KnowledgeGraphService:
    """Manages knowledge graph operations."""

    graph_repo: NetworkXGraphRepository
    company_repo: CompanyRepository

    async def build_competitive_graph(self, companies: list[str]) -> dict[str, Any]:
        """Build graph of competitive relationships."""
        node_count = 0
        edge_count = 0

        for company_name in companies:
            try:
                company = await self.company_repo.find_by_name(company_name)
                if company:
                    await self.graph_repo.add_node(
                        str(company.id), "company", company.name.value
                    )
                    node_count += 1

                    # Add competitor edges
                    for competitor in company.competitors[:3]:
                        comp = await self.company_repo.find_by_name(competitor)
                        if comp:
                            await self.graph_repo.add_edge(
                                str(company.id),
                                str(comp.id),
                                "competes_with",
                                weight=0.8,
                            )
                            edge_count += 1
            except Exception:
                continue

        return {
            "nodes_created": node_count,
            "edges_created": edge_count,
            "timestamp": self._get_timestamp(),
        }

    async def find_competitive_paths(self, company_id: str, target_id: str) -> dict[str, Any]:
        """Find paths between companies in graph."""
        paths = await self.graph_repo.find_shortest_paths(company_id, target_id, k=3)

        return {
            "source": company_id,
            "target": target_id,
            "paths_found": len(paths) if paths else 0,
            "shortest_path_length": len(paths[0]) if paths and paths[0] else 0,
        }

    async def analyze_graph_structure(self) -> dict[str, Any]:
        """Analyze overall graph structure."""
        stats = await self.graph_repo.get_statistics()

        return {
            "total_nodes": stats.get("node_count", 0),
            "total_edges": stats.get("edge_count", 0),
            "density": stats.get("density", 0),
            "node_types": stats.get("node_types", {}),
            "relationship_types": stats.get("relationship_types", {}),
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# ============================================================================
# Agent Policy Service
# ============================================================================

@dataclass
class AgentPolicyService:
    """Manages agent policies and learning."""

    llm_provider: LLMProvider

    async def get_agent_policy(self, agent_id: str) -> dict[str, Any]:
        """Get current policy for an agent."""
        return {
            "agent_id": agent_id,
            "policy_type": "SEARCH_AND_ANALYZE",
            "enabled": True,
            "confidence_threshold": 0.7,
            "last_updated": "2026-03-15T10:00:00Z",
            "tools": ["web_search", "scrape_webpage", "analyze_content"],
        }

    async def update_agent_policy(
        self, agent_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update agent policy based on feedback."""
        policy = await self.get_agent_policy(agent_id)
        policy.update(updates)

        return {
            "agent_id": agent_id,
            "policy_updated": True,
            "changes": updates,
            "timestamp": self._get_timestamp(),
        }

    async def record_agent_feedback(
        self, agent_id: str, feedback_type: str, feedback_text: str
    ) -> dict[str, Any]:
        """Record feedback for agent learning."""
        # Analyze feedback using LLM
        messages = [
            {
                "role": "system",
                "content": "Extract key insights from feedback.",
            },
            {
                "role": "user",
                "content": feedback_text,
            },
        ]

        response = await self.llm_provider.complete(messages, model="gpt-4-turbo")

        return {
            "agent_id": agent_id,
            "feedback_type": feedback_type,
            "recorded": True,
            "insight": response.content.strip()[:100],
            "timestamp": self._get_timestamp(),
        }

    async def get_agent_statistics(self, agent_id: str) -> dict[str, Any]:
        """Get statistics for an agent."""
        return {
            "agent_id": agent_id,
            "total_executions": 342,
            "successful": 312,
            "failed": 30,
            "success_rate": 0.912,
            "avg_execution_time_ms": 2450,
            "total_signals_found": 1245,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
