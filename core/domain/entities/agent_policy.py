"""
AgentPolicy Entity

Represents learned policies and strategies for agents.
Agents use policies to improve their performance over time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List, Dict, Any
from enum import Enum

from ..value_objects.entity_id import EntityId
from ..value_objects.confidence import Confidence
from ..value_objects.timestamp import Timestamp


class PolicyType(Enum):
    """Types of agent policies."""
    TOOL_SELECTION = "tool_selection"  # Which tools to use for tasks
    TASK_ORDERING = "task_ordering"  # Order of task execution
    MODEL_SELECTION = "model_selection"  # Which LLM to use
    SEARCH_STRATEGY = "search_strategy"  # How to search for information
    EXTRACTION_PATTERN = "extraction_pattern"  # Patterns for data extraction
    VALIDATION_RULE = "validation_rule"  # Rules for validation
    RETRY_STRATEGY = "retry_strategy"  # How to handle failures
    CUSTOM = "custom"


class PolicyStatus(Enum):
    """Status of a policy."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class PolicySource(Enum):
    """Source of the policy."""
    MANUAL = "manual"  # Manually configured
    LEARNED = "learned"  # Learned from feedback
    IMPORTED = "imported"  # Imported from another agent
    DEFAULT = "default"  # Default policy


@dataclass(frozen=True)
class ToolPreference:
    """
    Preference for using a specific tool.

    Used in tool selection policies.
    """

    tool_name: str
    weight: float  # 0.0 to 1.0
    success_rate: float  # 0.0 to 1.0
    avg_execution_time_ms: int = 0
    usage_count: int = 0

    def __post_init__(self) -> None:
        """Validate tool preference."""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("Tool weight must be between 0.0 and 1.0")
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError("Success rate must be between 0.0 and 1.0")
        if self.usage_count < 0:
            raise ValueError("Usage count cannot be negative")
        if self.avg_execution_time_ms < 0:
            raise ValueError("Execution time cannot be negative")


@dataclass(frozen=True)
class StrategyPattern:
    """
    A pattern or strategy that the agent can use.

    Examples: "search_first_then_browse", "deep_dive_then_summarize"
    """

    name: str
    description: str
    steps: List[str]  # Ordered list of steps
    success_rate: float  # 0.0 to 1.0
    avg_quality_score: float  # 0.0 to 1.0
    usage_count: int = 0
    last_used: Optional[Timestamp] = None

    def __post_init__(self) -> None:
        """Validate strategy pattern."""
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError("Success rate must be between 0.0 and 1.0")
        if not 0.0 <= self.avg_quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class AgentPolicy:
    """
    AgentPolicy entity representing learned behavior for an agent.

    Policies enable agents to improve over time through feedback loops.
    They contain tool preferences, successful strategies, and learned rules.

    Attributes:
        id: Unique identifier for the policy
        agent_id: ID of the agent this policy belongs to
        agent_type: Type of agent (research, analysis, strategy, etc.)
        policy_type: Type of policy (tool_selection, task_ordering, etc.)
        policy_source: How this policy was created
        status: Current status of the policy
        tool_preferences: Mapping of tools to their preference scores
        successful_strategies: Strategies that have worked well
        failed_approaches: Approaches that should be avoided
        model_preferences: Preferred LLM models for different task types
        validation_rules: Rules for validating agent outputs
        retry_config: Configuration for retry logic
        confidence: Confidence in this policy's effectiveness
        effectiveness_score: Computed effectiveness (0-100)
        usage_count: Number of times this policy was used
        feedback_count: Number of feedback items received
        last_successful: When this policy was last used successfully
        last_failed: When this policy last failed
        created_at: When this policy was created
        updated_at: When this policy was last updated
        metadata: Additional policy-specific data
    """

    id: EntityId
    agent_id: str
    agent_type: str
    policy_type: PolicyType
    policy_source: PolicySource = PolicySource.LEARNED
    status: PolicyStatus = PolicyStatus.ACTIVE
    tool_preferences: Dict[str, ToolPreference] = field(default_factory=dict)
    successful_strategies: List[StrategyPattern] = field(default_factory=list)
    failed_approaches: Set[str] = field(default_factory=set)
    model_preferences: Dict[str, str] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    confidence: Confidence = field(default_factory=lambda: Confidence.medium())
    effectiveness_score: int = 50
    usage_count: int = 0
    feedback_count: int = 0
    last_successful: Optional[Timestamp] = None
    last_failed: Optional[Timestamp] = None
    created_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    updated_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the agent policy."""
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
        if not self.agent_type:
            raise ValueError("Agent type cannot be empty")
        if not 0 <= self.effectiveness_score <= 100:
            raise ValueError("Effectiveness score must be between 0 and 100")
        if self.usage_count < 0:
            raise ValueError("Usage count cannot be negative")
        if self.feedback_count < 0:
            raise ValueError("Feedback count cannot be negative")

    @property
    def is_active(self) -> bool:
        """Check if policy is active."""
        return self.status == PolicyStatus.ACTIVE

    @property
    def is_effective(self) -> bool:
        """Check if policy is considered effective."""
        return self.effectiveness_score >= 70

    @property
    def top_strategy(self) -> Optional[StrategyPattern]:
        """Get the top strategy by success rate."""
        if not self.successful_strategies:
            return None
        return max(self.successful_strategies, key=lambda s: s.success_rate)

    @property
    def top_tool(self) -> Optional[tuple[str, ToolPreference]]:
        """Get the top tool by weight."""
        if not self.tool_preferences:
            return None
        return max(self.tool_preferences.items(), key=lambda x: x[1].weight)

    @property
    def days_since_last_success(self) -> Optional[int]:
        """Calculate days since last successful use."""
        if self.last_successful is None:
            return None
        return (Timestamp.now() - self.last_successful).days

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate from feedback."""
        if self.feedback_count == 0:
            return 0.5
        return (self.effectiveness_score / 100.0)

    def record_usage(self, successful: bool) -> "AgentPolicy":
        """Record a usage event and return updated policy."""
        new_usage_count = self.usage_count + 1
        new_feedback_count = self.feedback_count + 1

        # Update effectiveness score using simple exponential moving average
        alpha = 0.1
        feedback_score = 100 if successful else 0
        new_effectiveness = int(
            (1 - alpha) * self.effectiveness_score + alpha * feedback_score
        )

        return AgentPolicy(
            id=self.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            policy_type=self.policy_type,
            policy_source=self.policy_source,
            status=self.status,
            tool_preferences=self.tool_preferences,
            successful_strategies=self.successful_strategies,
            failed_approaches=self.failed_approaches,
            model_preferences=self.model_preferences,
            validation_rules=self.validation_rules,
            retry_config=self.retry_config,
            confidence=self.confidence,
            effectiveness_score=new_effectiveness,
            usage_count=new_usage_count,
            feedback_count=new_feedback_count,
            last_successful=Timestamp.now() if successful else self.last_successful,
            last_failed=Timestamp.now() if not successful else self.last_failed,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            metadata=self.metadata,
        )

    def add_tool_preference(self, preference: ToolPreference) -> "AgentPolicy":
        """Add or update a tool preference."""
        return AgentPolicy(
            id=self.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            policy_type=self.policy_type,
            policy_source=self.policy_source,
            status=self.status,
            tool_preferences={**self.tool_preferences, preference.tool_name: preference},
            successful_strategies=self.successful_strategies,
            failed_approaches=self.failed_approaches,
            model_preferences=self.model_preferences,
            validation_rules=self.validation_rules,
            retry_config=self.retry_config,
            confidence=self.confidence,
            effectiveness_score=self.effectiveness_score,
            usage_count=self.usage_count,
            feedback_count=self.feedback_count,
            last_successful=self.last_successful,
            last_failed=self.last_failed,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            metadata=self.metadata,
        )

    def add_strategy(self, strategy: StrategyPattern) -> "AgentPolicy":
        """Add a successful strategy."""
        # Update if exists, otherwise add
        updated_strategies = [
            s for s in self.successful_strategies if s.name != strategy.name
        ] + [strategy]

        return AgentPolicy(
            id=self.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            policy_type=self.policy_type,
            policy_source=self.policy_source,
            status=self.status,
            tool_preferences=self.tool_preferences,
            successful_strategies=updated_strategies,
            failed_approaches=self.failed_approaches,
            model_preferences=self.model_preferences,
            validation_rules=self.validation_rules,
            retry_config=self.retry_config,
            confidence=self.confidence,
            effectiveness_score=self.effectiveness_score,
            usage_count=self.usage_count,
            feedback_count=self.feedback_count,
            last_successful=self.last_successful,
            last_failed=self.last_failed,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            metadata=self.metadata,
        )

    def add_failed_approach(self, approach: str) -> "AgentPolicy":
        """Add a failed approach to avoid."""
        return AgentPolicy(
            id=self.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            policy_type=self.policy_type,
            policy_source=self.policy_source,
            status=self.status,
            tool_preferences=self.tool_preferences,
            successful_strategies=self.successful_strategies,
            failed_approaches=self.failed_approaches | {approach},
            model_preferences=self.model_preferences,
            validation_rules=self.validation_rules,
            retry_config=self.retry_config,
            confidence=self.confidence,
            effectiveness_score=self.effectiveness_score,
            usage_count=self.usage_count,
            feedback_count=self.feedback_count,
            last_successful=self.last_successful,
            last_failed=self.last_failed,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            metadata=self.metadata,
        )

    def with_status(self, status: PolicyStatus) -> "AgentPolicy":
        """Update policy status."""
        return AgentPolicy(
            id=self.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            policy_type=self.policy_type,
            policy_source=self.policy_source,
            status=status,
            tool_preferences=self.tool_preferences,
            successful_strategies=self.successful_strategies,
            failed_approaches=self.failed_approaches,
            model_preferences=self.model_preferences,
            validation_rules=self.validation_rules,
            retry_config=self.retry_config,
            confidence=self.confidence,
            effectiveness_score=self.effectiveness_score,
            usage_count=self.usage_count,
            feedback_count=self.feedback_count,
            last_successful=self.last_successful,
            last_failed=self.last_failed,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            metadata=self.metadata,
        )

    @classmethod
    def create(
        cls,
        agent_id: str,
        agent_type: str,
        policy_type: PolicyType,
    ) -> "AgentPolicy":
        """Factory method to create a new AgentPolicy."""
        return cls(
            id=EntityId.generate(),
            agent_id=agent_id,
            agent_type=agent_type,
            policy_type=policy_type,
        )


@dataclass(frozen=True)
class PolicyFeedback:
    """
    Feedback received about a policy.

    Used to update and improve agent policies.
    """

    id: EntityId
    policy_id: EntityId
    agent_id: str
    task_id: Optional[str]
    was_successful: bool
    quality_score: float  # 0.0 to 1.0
    execution_time_ms: int
    notes: Optional[str] = None
    created_at: Timestamp = field(default_factory=lambda: Timestamp.now())

    @property
    def is_high_quality(self) -> bool:
        """Check if this was high-quality feedback."""
        return self.quality_score >= 0.8


__all__ = [
    "AgentPolicy",
    "PolicyType",
    "PolicyStatus",
    "PolicySource",
    "ToolPreference",
    "StrategyPattern",
    "PolicyFeedback",
]