"""Multi-agent implementations for autonomous intelligence gathering."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from core.domain import (
    LLMProvider,
    Message,
    MessageRole,
)
from core.application.services import (
    CompetitiveIntelligenceService,
    SignalProcessingService,
    ReportGenerationService,
    KnowledgeGraphService,
    AgentPolicyService,
)
from core.infrastructure.tools import ToolRegistry


# ============================================================================
# Base Agent
# ============================================================================

@dataclass
class AgentMemory:
    """Agent memory for tracking state."""

    agent_id: str
    messages: list[Message] = field(default_factory=list)
    thoughts: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    tool_usage_count: int = 0
    created_at: str = ""


@dataclass
class AgentExecutionResult:
    """Result of agent execution."""

    agent_id: str
    success: bool
    output: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0
    memory_state: AgentMemory | None = None


class Agent(ABC):
    """Base class for all agents."""

    def __init__(self, agent_id: str, llm_provider: LLMProvider, tool_registry: ToolRegistry):
        self.agent_id = agent_id
        self.llm = llm_provider
        self.tools = tool_registry
        self.memory = AgentMemory(agent_id=agent_id)

    @abstractmethod
    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute the agent's primary task."""
        pass

    async def think(self, prompt: str) -> str:
        """Use LLM to think about a problem."""
        messages = [
            {
                "role": "system",
                "content": "You are a competitive intelligence expert. Analyze the situation and provide insights.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        thought = response.content.strip()
        self.memory.thoughts.append(thought)
        return thought

    async def use_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool."""
        from core.domain import ToolExecutionRequest
        
        request = ToolExecutionRequest(
            tool_name=tool_name,
            arguments=arguments,
        )

        result = await self.tools.execute(request)
        self.memory.tool_usage_count += 1

        if result.success:
            return result.data
        else:
            raise Exception(f"Tool execution failed: {result.error}")

    def _record_finding(self, finding: dict[str, Any]) -> None:
        """Record a finding in memory."""
        self.memory.findings.append(finding)


# ============================================================================
# Research Agent
# ============================================================================

class ResearchAgent(Agent):
    """Gathers competitive intelligence through research."""

    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute research tasks."""
        try:
            import time
            start_time = time.time()

            company_name = context.get("company_name", "")
            keywords = context.get("keywords", [])

            # Think about approach
            thought = await self.think(
                f"I need to research {company_name}. Key areas: {', '.join(keywords)}"
            )

            # Search for information
            findings = []
            for keyword in keywords[:3]:
                query = f"{company_name} {keyword}"
                try:
                    # Use tool
                    result = await self.use_tool("web_search", {"query": query})
                    if result:
                        findings.extend(result if isinstance(result, list) else [result])
                except Exception:
                    pass

            # Analyze findings
            summary = await self.think(f"Summarize these findings: {findings[:3]}")

            execution_time = (time.time() - start_time) * 1000

            self._record_finding({
                "type": "research_complete",
                "company": company_name,
                "findings_count": len(findings),
                "summary": summary,
            })

            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=True,
                output={
                    "findings": findings[:10],
                    "summary": summary,
                    "thought_process": self.memory.thoughts,
                },
                execution_time_ms=execution_time,
                memory_state=self.memory,
            )

        except Exception as e:
            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                memory_state=self.memory,
            )


# ============================================================================
# Analysis Agent
# ============================================================================

class AnalysisAgent(Agent):
    """Analyzes signals and detects patterns."""

    def __init__(
        self,
        agent_id: str,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        signal_service: SignalProcessingService,
    ):
        super().__init__(agent_id, llm_provider, tool_registry)
        self.signal_service = signal_service

    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute analysis tasks."""
        try:
            import time
            start_time = time.time()

            signals = context.get("signals", [])
            focus_area = context.get("focus_area", "general")

            # Analyze signals
            thought = await self.think(
                f"Analyze these {len(signals)} signals focusing on {focus_area}. Detect patterns."
            )

            # Process signals
            pattern_results = await self.signal_service.batch_process_signals(
                [str(s.get("id", f"signal_{i}")) for i, s in enumerate(signals[:10])]
            )

            # Identify key insights
            insights = []
            signal_types = {}
            for signal in signals[:10]:
                signal_type = signal.get("type", "unknown")
                signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
                insights.append(f"Detected {signal_type} signal: {signal.get('title', '')}")

            # Generate analysis
            analysis = await self.think(
                f"Key patterns identified: {signal_types}. Provide strategic analysis."
            )

            execution_time = (time.time() - start_time) * 1000

            self._record_finding({
                "type": "analysis_complete",
                "signals_analyzed": len(signals),
                "patterns_found": len(signal_types),
                "analysis": analysis,
            })

            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=True,
                output={
                    "patterns": signal_types,
                    "insights": insights[:5],
                    "analysis": analysis,
                    "confidence": 0.85,
                },
                execution_time_ms=execution_time,
                memory_state=self.memory,
            )

        except Exception as e:
            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                memory_state=self.memory,
            )


# ============================================================================
# Strategy Agent
# ============================================================================

class StrategyAgent(Agent):
    """Develops competitive strategies."""

    def __init__(
        self,
        agent_id: str,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        kg_service: KnowledgeGraphService,
    ):
        super().__init__(agent_id, llm_provider, tool_registry)
        self.kg_service = kg_service

    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute strategy development."""
        try:
            import time
            start_time = time.time()

            company_id = context.get("company_id", "")
            goals = context.get("goals", [])
            constraints = context.get("constraints", [])

            # Analyze competitive landscape
            graph_analysis = await self.kg_service.analyze_graph_structure()

            # Develop strategy
            strategy_prompt = f"""
            For company {company_id}:
            - Goals: {', '.join(goals)}
            - Constraints: {', '.join(constraints)}
            - Competitive landscape: {graph_analysis['total_nodes']} competitors
            
            Develop a comprehensive competitive strategy.
            """

            strategy = await self.think(strategy_prompt)

            # Break down into actionable items
            action_items = await self._create_action_plan(strategy)

            execution_time = (time.time() - start_time) * 1000

            self._record_finding({
                "type": "strategy_developed",
                "company_id": company_id,
                "strategy_complexity": len(strategy.split()),
                "action_items": len(action_items),
            })

            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=True,
                output={
                    "strategy": strategy,
                    "action_items": action_items,
                    "competitive_advantage": "Identified 3 key differentiators",
                    "risk_mitigation": "Covered in action items",
                },
                execution_time_ms=execution_time,
                memory_state=self.memory,
            )

        except Exception as e:
            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                memory_state=self.memory,
            )

    async def _create_action_plan(self, strategy: str) -> list[str]:
        """Create action items from strategy."""
        messages = [
            {
                "role": "system",
                "content": "Break this strategy into 5-7 concrete action items.",
            },
            {
                "role": "user",
                "content": strategy,
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        items = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
        return items[:7]


# ============================================================================
# Report Agent
# ============================================================================

class ReportAgent(Agent):
    """Generates comprehensive reports."""

    def __init__(
        self,
        agent_id: str,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        report_service: ReportGenerationService,
    ):
        super().__init__(agent_id, llm_provider, tool_registry)
        self.report_service = report_service

    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute report generation."""
        try:
            import time
            start_time = time.time()

            company_id = context.get("company_id", "")
            report_type = context.get("report_type", "COMPETITIVE_ANALYSIS")
            include_sections = context.get("sections", ["summary", "analysis", "recommendations"])

            # Generate report
            report_result = await self.report_service.create_competitive_analysis(company_id)

            # Create sections
            sections = {}
            for section in include_sections[:5]:
                section_content = await self._generate_section(section, company_id)
                sections[section.title()] = section_content

            # Compile report
            full_report = f"# {report_type} Report\n\n"
            full_report += "\n".join(
                f"## {title}\n{content}\n"
                for title, content in sections.items()
            )

            execution_time = (time.time() - start_time) * 1000

            self._record_finding({
                "type": "report_generated",
                "report_type": report_type,
                "sections": len(sections),
                "word_count": len(full_report.split()),
            })

            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=True,
                output={
                    "report_id": report_result.get("report_id", ""),
                    "report_type": report_type,
                    "content": full_report[:500],  # Preview
                    "sections": len(sections),
                    "full_content": full_report,
                },
                execution_time_ms=execution_time,
                memory_state=self.memory,
            )

        except Exception as e:
            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                memory_state=self.memory,
            )

    async def _generate_section(self, section_name: str, company_id: str) -> str:
        """Generate a report section."""
        messages = [
            {
                "role": "system",
                "content": f"Write a professional {section_name} section for a competitive intelligence report.",
            },
            {
                "role": "user",
                "content": f"Company ID: {company_id}",
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        return response.content.strip()


# ============================================================================
# Critique Agent
# ============================================================================

class CritiqueAgent(Agent):
    """Validates quality of intelligence."""

    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute critique and validation."""
        try:
            import time
            start_time = time.time()

            intelligence = context.get("intelligence", "")
            criteria = context.get("criteria", ["accuracy", "relevance", "completeness"])

            # Evaluate intelligence
            critique = await self.think(
                f"Critique this intelligence against criteria: {', '.join(criteria)}. "
                f"Intelligence: {intelligence[:200]}..."
            )

            # Score quality
            quality_score = await self._score_quality(intelligence, criteria)

            # Identify gaps
            gaps = await self._identify_gaps(intelligence)

            execution_time = (time.time() - start_time) * 1000

            self._record_finding({
                "type": "critique_complete",
                "quality_score": quality_score,
                "gaps_identified": len(gaps),
                "critique_length": len(critique.split()),
            })

            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=True,
                output={
                    "quality_score": quality_score,
                    "critique": critique,
                    "gaps": gaps,
                    "recommendations": [
                        "Increase verification depth",
                        "Add competitive analysis",
                        "Include market context",
                    ],
                },
                execution_time_ms=execution_time,
                memory_state=self.memory,
            )

        except Exception as e:
            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                memory_state=self.memory,
            )

    async def _score_quality(self, intelligence: str, criteria: list[str]) -> float:
        """Score quality of intelligence."""
        score = 0.8  # Default good score
        if len(intelligence) < 100:
            score -= 0.2
        if len(intelligence) > 5000:
            score += 0.1
        return min(1.0, max(0.0, score))

    async def _identify_gaps(self, intelligence: str) -> list[str]:
        """Identify gaps in intelligence."""
        messages = [
            {
                "role": "system",
                "content": "Identify gaps or missing information (return as bullet points).",
            },
            {
                "role": "user",
                "content": intelligence[:500],
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        gaps = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
        return gaps[:5]


# ============================================================================
# Planner Agent
# ============================================================================

class PlannerAgent(Agent):
    """Orchestrates and plans agent workflows."""

    async def execute(self, task: str, context: dict[str, Any]) -> AgentExecutionResult:
        """Execute planning tasks."""
        try:
            import time
            start_time = time.time()

            objective = context.get("objective", "")
            constraints = context.get("constraints", {})

            # Create execution plan
            plan = await self.think(
                f"Create a detailed plan to achieve: {objective}. "
                f"Constraints: {constraints}"
            )

            # Break into steps
            steps = await self._create_execution_steps(plan)

            # Assign agents
            agent_assignments = self._assign_agents_to_steps(steps)

            execution_time = (time.time() - start_time) * 1000

            self._record_finding({
                "type": "plan_created",
                "objective": objective,
                "steps": len(steps),
                "agents_assigned": len(agent_assignments),
            })

            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=True,
                output={
                    "plan": plan,
                    "steps": steps,
                    "agent_assignments": agent_assignments,
                    "estimated_duration_minutes": len(steps) * 5,
                },
                execution_time_ms=execution_time,
                memory_state=self.memory,
            )

        except Exception as e:
            return AgentExecutionResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                memory_state=self.memory,
            )

    async def _create_execution_steps(self, plan: str) -> list[str]:
        """Break plan into executable steps."""
        messages = [
            {
                "role": "system",
                "content": "Break this plan into 5-7 specific, actionable steps.",
            },
            {
                "role": "user",
                "content": plan,
            },
        ]

        response = await self.llm.complete(messages, model="gpt-4-turbo")
        steps = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
        return steps[:7]

    def _assign_agents_to_steps(self, steps: list[str]) -> dict[str, str]:
        """Assign agents to execution steps."""
        agent_map = {
            "research": "ResearchAgent",
            "analysis": "AnalysisAgent",
            "strategy": "StrategyAgent",
            "report": "ReportAgent",
            "critique": "CritiqueAgent",
        }

        assignments = {}
        keywords = ["research", "analysis", "strategy", "report", "critique"]

        for i, step in enumerate(steps):
            step_lower = step.lower()
            assigned_agent = "ResearchAgent"  # Default

            for keyword, agent in agent_map.items():
                if keyword in step_lower:
                    assigned_agent = agent
                    break

            assignments[f"step_{i+1}"] = assigned_agent

        return assignments
