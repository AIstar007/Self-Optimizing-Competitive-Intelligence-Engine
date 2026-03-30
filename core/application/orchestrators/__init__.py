"""Multi-agent orchestration and workflow management."""

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine
from enum import Enum

from core.application.agents import (
    Agent,
    ResearchAgent,
    AnalysisAgent,
    StrategyAgent,
    ReportAgent,
    CritiqueAgent,
    PlannerAgent,
    AgentExecutionResult,
)
from core.domain import LLMProvider
from core.infrastructure.tools import ToolRegistry


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


class TaskStatus(str, Enum):
    """Status of individual task."""

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class WorkflowTask:
    """Individual task in workflow."""

    task_id: str
    agent_type: str  # Type of agent to execute
    description: str
    context: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: AgentExecutionResult | None = None
    created_at: str = ""
    completed_at: str | None = None


@dataclass
class WorkflowExecution:
    """Execution of a workflow."""

    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    tasks: list[WorkflowTask] = field(default_factory=list)
    results: list[AgentExecutionResult] = field(default_factory=list)
    created_at: str = ""
    completed_at: str | None = None
    total_execution_time_ms: float = 0.0


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
    ):
        self.llm = llm_provider
        self.tools = tool_registry
        self.agents: dict[str, Agent] = {}
        self.workflows: dict[str, WorkflowExecution] = {}
        self._initialize_agents()

    def _initialize_agents(self) -> None:
        """Initialize all agents."""
        from core.application.services import (
            SignalProcessingService,
            ReportGenerationService,
            KnowledgeGraphService,
        )

        # For now, create minimal service instances (in production, use DI)
        self.agents["research"] = ResearchAgent("agent_research", self.llm, self.tools)
        self.agents["analysis"] = AnalysisAgent(
            "agent_analysis", self.llm, self.tools, None  # signal_service placeholder
        )
        self.agents["strategy"] = StrategyAgent(
            "agent_strategy", self.llm, self.tools, None  # kg_service placeholder
        )
        self.agents["report"] = ReportAgent(
            "agent_report", self.llm, self.tools, None  # report_service placeholder
        )
        self.agents["critique"] = CritiqueAgent("agent_critique", self.llm, self.tools)
        self.agents["planner"] = PlannerAgent("agent_planner", self.llm, self.tools)

    async def execute_workflow(
        self, workflow_id: str, tasks: list[WorkflowTask]
    ) -> WorkflowExecution:
        """Execute a workflow with multiple tasks."""
        import time

        workflow = WorkflowExecution(workflow_id=workflow_id)
        start_time = time.time()

        try:
            workflow.status = WorkflowStatus.RUNNING
            workflow.tasks = tasks

            # Execute tasks in order, respecting dependencies
            for task in tasks:
                result = await self._execute_task(task, workflow)
                workflow.results.append(result)

                if not result.success:
                    # Continue on non-critical failures
                    task.status = TaskStatus.FAILED
                else:
                    task.status = TaskStatus.COMPLETED

            workflow.status = WorkflowStatus.COMPLETED

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED

        workflow.total_execution_time_ms = (time.time() - start_time) * 1000
        self.workflows[workflow_id] = workflow
        return workflow

    async def _execute_task(
        self, task: WorkflowTask, workflow: WorkflowExecution
    ) -> AgentExecutionResult:
        """Execute a single task."""
        # Check dependencies
        for dep_id in task.dependencies:
            dep_task = next((t for t in workflow.tasks if t.task_id == dep_id), None)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                return AgentExecutionResult(
                    agent_id=task.agent_type,
                    success=False,
                    error=f"Dependency {dep_id} not completed",
                )

        # Get agent
        agent = self.agents.get(task.agent_type.lower())
        if not agent:
            return AgentExecutionResult(
                agent_id=task.agent_type,
                success=False,
                error=f"Agent type {task.agent_type} not found",
            )

        # Execute agent
        task.status = TaskStatus.RUNNING
        result = await agent.execute(task.description, task.context)
        task.result = result

        return result

    async def create_competitive_intelligence_workflow(
        self, company_id: str, company_name: str
    ) -> WorkflowExecution:
        """Create and execute competitive intelligence workflow."""
        workflow_id = f"ci_workflow_{company_id}"

        tasks = [
            WorkflowTask(
                task_id="task_research",
                agent_type="research",
                description=f"Research {company_name}",
                context={
                    "company_name": company_name,
                    "company_id": company_id,
                    "keywords": ["funding", "partnerships", "products", "leadership"],
                },
            ),
            WorkflowTask(
                task_id="task_analysis",
                agent_type="analysis",
                description="Analyze discovered signals",
                context={
                    "company_id": company_id,
                    "signals": [],
                    "focus_area": "competitive_threats",
                },
                dependencies=["task_research"],
            ),
            WorkflowTask(
                task_id="task_strategy",
                agent_type="strategy",
                description="Develop competitive strategy",
                context={
                    "company_id": company_id,
                    "goals": ["market_leadership", "innovation"],
                    "constraints": ["budget", "timeline"],
                },
                dependencies=["task_analysis"],
            ),
            WorkflowTask(
                task_id="task_report",
                agent_type="report",
                description="Generate intelligence report",
                context={
                    "company_id": company_id,
                    "report_type": "COMPETITIVE_ANALYSIS",
                    "sections": ["summary", "analysis", "strategy", "recommendations"],
                },
                dependencies=["task_strategy"],
            ),
            WorkflowTask(
                task_id="task_critique",
                agent_type="critique",
                description="Review and validate intelligence",
                context={
                    "intelligence": "Complete competitive intelligence package",
                    "criteria": ["accuracy", "relevance", "actionability", "completeness"],
                },
                dependencies=["task_report"],
            ),
        ]

        return await self.execute_workflow(workflow_id, tasks)

    async def create_market_analysis_workflow(
        self, markets: list[str]
    ) -> WorkflowExecution:
        """Create workflow for market analysis."""
        workflow_id = f"market_workflow_{len(markets)}"

        tasks = [
            WorkflowTask(
                task_id="task_planner",
                agent_type="planner",
                description="Plan market analysis",
                context={
                    "objective": f"Analyze {len(markets)} markets",
                    "constraints": {"time_limit": "2_hours", "resource_limit": "normal"},
                },
            ),
            WorkflowTask(
                task_id="task_research",
                agent_type="research",
                description=f"Research markets: {', '.join(markets)}",
                context={
                    "markets": markets,
                    "keywords": ["trends", "players", "opportunities"],
                },
                dependencies=["task_planner"],
            ),
            WorkflowTask(
                task_id="task_analysis",
                agent_type="analysis",
                description="Analyze market signals and trends",
                context={
                    "markets": markets,
                    "focus_area": "market_dynamics",
                },
                dependencies=["task_research"],
            ),
            WorkflowTask(
                task_id="task_report",
                agent_type="report",
                description="Generate market overview",
                context={
                    "report_type": "MARKET_OVERVIEW",
                    "markets": markets,
                    "sections": ["trends", "players", "opportunities", "threats"],
                },
                dependencies=["task_analysis"],
            ),
        ]

        return await self.execute_workflow(workflow_id, tasks)

    def get_workflow(self, workflow_id: str) -> WorkflowExecution | None:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> list[WorkflowExecution]:
        """List all workflows."""
        return list(self.workflows.values())

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """Get detailed workflow status."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        task_statuses = {task.task_id: task.status.value for task in workflow.tasks}
        result_count = len([r for r in workflow.results if r.success])

        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "total_tasks": len(workflow.tasks),
            "completed_tasks": result_count,
            "task_statuses": task_statuses,
            "total_execution_time_ms": workflow.total_execution_time_ms,
            "completion_percentage": int((result_count / len(workflow.tasks) * 100)) if workflow.tasks else 0,
        }


class TaskScheduler:
    """Schedules and manages agent tasks."""

    def __init__(self):
        self.scheduled_tasks: dict[str, dict[str, Any]] = {}
        self.task_history: list[dict[str, Any]] = []

    def schedule_task(
        self,
        task_id: str,
        agent_type: str,
        context: dict[str, Any],
        schedule: str = "immediate",
        recurring: bool = False,
    ) -> dict[str, Any]:
        """Schedule a task for execution."""
        self.scheduled_tasks[task_id] = {
            "agent_type": agent_type,
            "context": context,
            "schedule": schedule,
            "recurring": recurring,
            "created_at": self._get_timestamp(),
        }

        return {
            "task_id": task_id,
            "scheduled": True,
            "schedule": schedule,
        }

    def get_scheduled_tasks(self, agent_type: str | None = None) -> list[dict[str, Any]]:
        """Get scheduled tasks."""
        tasks = list(self.scheduled_tasks.values())
        if agent_type:
            tasks = [t for t in tasks if t["agent_type"] == agent_type]
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            return True
        return False

    def record_execution(self, task_id: str, result: dict[str, Any]) -> None:
        """Record task execution."""
        self.task_history.append({
            "task_id": task_id,
            "result": result,
            "timestamp": self._get_timestamp(),
        })

    def get_task_history(self, task_id: str | None = None) -> list[dict[str, Any]]:
        """Get task execution history."""
        if task_id:
            return [h for h in self.task_history if h["task_id"] == task_id]
        return self.task_history

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class AgentCommunicator:
    """Facilitates communication between agents."""

    def __init__(self):
        self.message_queue: list[dict[str, Any]] = []
        self.agent_channels: dict[str, list[dict[str, Any]]] = {}

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Any,
    ) -> dict[str, Any]:
        """Send message between agents."""
        message = {
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "content": content,
            "timestamp": self._get_timestamp(),
        }

        self.message_queue.append(message)

        if to_agent not in self.agent_channels:
            self.agent_channels[to_agent] = []

        self.agent_channels[to_agent].append(message)

        return {
            "message_id": len(self.message_queue) - 1,
            "sent": True,
            "to": to_agent,
        }

    async def get_messages(self, agent_id: str) -> list[dict[str, Any]]:
        """Get messages for an agent."""
        return self.agent_channels.get(agent_id, [])

    async def clear_messages(self, agent_id: str) -> None:
        """Clear messages for an agent."""
        if agent_id in self.agent_channels:
            self.agent_channels[agent_id] = []

    def get_message_statistics(self) -> dict[str, Any]:
        """Get message statistics."""
        return {
            "total_messages": len(self.message_queue),
            "agents_with_messages": len(self.agent_channels),
            "channels": {
                agent: len(messages)
                for agent, messages in self.agent_channels.items()
            },
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
