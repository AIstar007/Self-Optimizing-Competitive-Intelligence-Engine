"""
Signal Entity

Represents a competitive intelligence signal detected from various sources.
Signals are key indicators of company activity, market changes, or events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List, Dict, Any
from enum import Enum

from ..value_objects.entity_id import EntityId
from ..value_objects.money import Money
from ..value_objects.confidence import Confidence
from ..value_objects.timestamp import Timestamp


class SignalType(Enum):
    """Types of signals that can be detected."""
    FUNDING_ANNOUNCEMENT = "funding_announcement"
    HIRING_SPIKE = "hiring_spike"
    PRODUCT_LAUNCH = "product_launch"
    PARTNERSHIP_ANNOUNCEMENT = "partnership_announcement"
    ACQUISITION_ANNOUNCEMENT = "acquisition_announcement"
    EXECUTIVE_CHANGE = "executive_change"
    MARKET_ENTRY = "market_entry"
    MARKET_EXIT = "market_exit"
    TECHNOLOGY_ADOPTION = "technology_adoption"
    REGULATORY_CHANGE = "regulatory_change"
    PRICING_CHANGE = "pricing_change"
    FEATURE_RELEASE = "feature_release"
    OUTAGE_OR_INCIDENT = "outage_or_incident"
    STRATEGIC_PIVOT = "strategic_pivot"
    CUSTOMER_WIN = "customer_win"
    CUSTOMER_LOSS = "customer_loss"
    COMPETITIVE_MOVE = "competitive_move"
    OTHER = "other"


class SignalSeverity(Enum):
    """Severity level of a signal."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignalSource(Enum):
    """Sources of intelligence signals."""
    NEWS_ARTICLE = "news_article"
    PRESS_RELEASE = "press_release"
    SOCIAL_MEDIA = "social_media"
    COMPANY_BLOG = "company_blog"
    JOB_POSTING = "job_posting"
    SEC_FILING = "sec_filing"
    REGISTRY_FILING = "registry_filing"
    WEBSITE_CHANGE = "website_change"
    ANALYST_REPORT = "analyst_report"
    INTERNAL_RESEARCH = "internal_research"
    CUSTOM_FEED = "custom_feed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Signal:
    """
    Signal entity representing a detected competitive intelligence signal.

    Signals are key indicators detected from various sources that may
    indicate important company or market changes.

    Attributes:
        id: Unique identifier for the signal
        type: Type/category of the signal
        company_id: ID of the company this signal relates to (optional)
        entity_name: Name of the entity (company, product, etc.)
        title: Brief title describing the signal
        description: Detailed description of the signal
        source: Source of the signal
        source_url: URL where signal was found
        severity: Importance/urgency of the signal
        confidence: Confidence level in the signal validity
        detected_at: When the signal was detected
        occurred_at: When the event actually occurred
        verified_at: When the signal was verified
        is_verified: Whether the signal has been verified
        tags: Tags for categorization
        metadata: Additional signal-specific data
        related_signals: IDs of related signals
        parent_signal_id: ID of parent signal if this is derived
        impact_score: Computed impact score (0-100)
        created_at: When this signal was created
        updated_at: When this signal was last updated
    """

    id: EntityId
    type: SignalType
    entity_name: str
    title: str
    description: str
    source: SignalSource
    source_url: Optional[str] = None
    company_id: Optional[EntityId] = None
    severity: SignalSeverity = SignalSeverity.MEDIUM
    confidence: Confidence = field(default_factory=lambda: Confidence.medium())
    detected_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    occurred_at: Optional[Timestamp] = None
    verified_at: Optional[Timestamp] = None
    is_verified: bool = False
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_signals: Set[EntityId] = field(default_factory=set)
    parent_signal_id: Optional[EntityId] = None
    impact_score: int = 50
    created_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    updated_at: Timestamp = field(default_factory=lambda: Timestamp.now())

    def __post_init__(self) -> None:
        """Validate the signal entity."""
        if not self.entity_name or not self.entity_name.strip():
            raise ValueError("Entity name cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("Signal title cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Signal description cannot be empty")
        if not 0 <= self.impact_score <= 100:
            raise ValueError("Impact score must be between 0 and 100")

    @property
    def is_critical(self) -> bool:
        """Check if signal is critical."""
        return self.severity == SignalSeverity.CRITICAL

    @property
    def is_high_priority(self) -> bool:
        """Check if signal requires immediate attention."""
        return self.severity in {SignalSeverity.HIGH, SignalSeverity.CRITICAL}

    @property
    def age_days(self) -> Optional[int]:
        """Calculate age of the signal in days."""
        if self.occurred_at is None:
            return None
        return (Timestamp.now() - self.occurred_at).days

    @property
    def source_display(self) -> str:
        """Get human-readable source name."""
        return self.source.value.replace("_", " ").title()

    def verify(self) -> "Signal":
        """Mark signal as verified and return new instance."""
        return Signal(
            id=self.id,
            type=self.type,
            company_id=self.company_id,
            entity_name=self.entity_name,
            title=self.title,
            description=self.description,
            source=self.source,
            source_url=self.source_url,
            severity=self.severity,
            confidence=Confidence.HIGH,
            detected_at=self.detected_at,
            occurred_at=self.occurred_at,
            verified_at=Timestamp.now(),
            is_verified=True,
            tags=self.tags,
            metadata=self.metadata,
            related_signals=self.related_signals,
            parent_signal_id=self.parent_signal_id,
            impact_score=self.impact_score,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    def add_related_signal(self, signal_id: EntityId) -> "Signal":
        """Add a related signal and return new instance."""
        return Signal(
            id=self.id,
            type=self.type,
            company_id=self.company_id,
            entity_name=self.entity_name,
            title=self.title,
            description=self.description,
            source=self.source,
            source_url=self.source_url,
            severity=self.severity,
            confidence=self.confidence,
            detected_at=self.detected_at,
            occurred_at=self.occurred_at,
            verified_at=self.verified_at,
            is_verified=self.is_verified,
            tags=self.tags,
            metadata=self.metadata,
            related_signals=self.related_signals | {signal_id},
            parent_signal_id=self.parent_signal_id,
            impact_score=self.impact_score,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    def add_tag(self, tag: str) -> "Signal":
        """Add a tag and return new instance."""
        return Signal(
            id=self.id,
            type=self.type,
            company_id=self.company_id,
            entity_name=self.entity_name,
            title=self.title,
            description=self.description,
            source=self.source,
            source_url=self.source_url,
            severity=self.severity,
            confidence=self.confidence,
            detected_at=self.detected_at,
            occurred_at=self.occurred_at,
            verified_at=self.verified_at,
            is_verified=self.is_verified,
            tags=self.tags | {tag.lower().strip()},
            metadata=self.metadata,
            related_signals=self.related_signals,
            parent_signal_id=self.parent_signal_id,
            impact_score=self.impact_score,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    def with_impact_score(self, score: int) -> "Signal":
        """Return new Signal with updated impact score."""
        return Signal(
            id=self.id,
            type=self.type,
            company_id=self.company_id,
            entity_name=self.entity_name,
            title=self.title,
            description=self.description,
            source=self.source,
            source_url=self.source_url,
            severity=self.severity,
            confidence=self.confidence,
            detected_at=self.detected_at,
            occurred_at=self.occurred_at,
            verified_at=self.verified_at,
            is_verified=self.is_verified,
            tags=self.tags,
            metadata=self.metadata,
            related_signals=self.related_signals,
            parent_signal_id=self.parent_signal_id,
            impact_score=max(0, min(100, score)),
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    @classmethod
    def create(
        cls,
        signal_type: SignalType,
        entity_name: str,
        title: str,
        description: str,
        source: SignalSource,
        source_url: Optional[str] = None,
        company_id: Optional[EntityId] = None,
    ) -> "Signal":
        """Factory method to create a new Signal."""
        return cls(
            id=EntityId.generate(),
            type=signal_type,
            entity_name=entity_name,
            title=title,
            description=description,
            source=source,
            source_url=source_url,
            company_id=company_id,
        )


@dataclass(frozen=True)
class SignalPattern:
    """
    Represents a pattern detected across multiple signals.

    Patterns are higher-level insights derived from signal analysis.
    """

    id: EntityId
    name: str
    description: str
    signal_ids: Set[EntityId]
    pattern_type: str
    frequency: int
    first_seen: Timestamp
    last_seen: Timestamp
    confidence: Confidence = field(default_factory=lambda: Confidence.medium())
    impact_score: int = 50
    created_at: Timestamp = field(default_factory=lambda: Timestamp.now())

    @property
    def signal_count(self) -> int:
        """Number of signals in this pattern."""
        return len(self.signal_ids)

    @property
    def is_emerging(self) -> bool:
        """Check if this is an emerging pattern (recent)."""
        return (Timestamp.now() - self.first_seen).days <= 30


__all__ = [
    "Signal",
    "SignalType",
    "SignalSeverity",
    "SignalSource",
    "SignalPattern",
]