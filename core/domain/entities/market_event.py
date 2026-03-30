"""
MarketEvent Entity

Represents a significant market event or trend.
MarketEvents are broader than signals and affect multiple entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List, Dict, Any
from enum import Enum

from ..value_objects.entity_id import EntityId
from ..value_objects.money import Money
from ..value_objects.confidence import Confidence
from ..value_objects.timestamp import Timestamp


class MarketEventType(Enum):
    """Types of market events."""
    MARKET_ENTRY = "market_entry"
    MARKET_EXIT = "market_exit"
    MERGER_ACQUISITION = "merger_acquisition"
    IPO = "ipo"
    REGULATORY_CHANGE = "regulatory_change"
    TECHNOLOGY_BREAKTHROUGH = "technology_breakthrough"
    ECONOMIC_SHIFT = "economic_shift"
    INDUSTRY_TREND = "industry_trend"
    CONSUMER_BEHAVIOR_CHANGE = "consumer_behavior_change"
    SUPPLY_CHAIN_DISRUPTION = "supply_chain_disruption"
    GEOPOLITICAL_EVENT = "geopolitical_event"
    NATURAL_DISASTER = "natural_disaster"
    PANDEMIC_HEALTH_EVENT = "pandemic_health_event"
    COMPETITIVE_LANDSCAPE_SHIFT = "competitive_landscape_shift"
    PRICE_WAR = "price_war"
    MARKET_CONSOLIDATION = "market_consolidation"
    OTHER = "other"


class MarketEventImpact(Enum):
    """Impact level of a market event."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    MAJOR = "major"
    TRANSFORMATIONAL = "transformational"


class MarketEventDuration(Enum):
    """Expected duration of the market event."""
    ONE_TIME = "one_time"
    SHORT_TERM = "short_term"  # Days to weeks
    MEDIUM_TERM = "medium_term"  # Weeks to months
    LONG_TERM = "long_term"  # Months to years
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MarketEvent:
    """
    MarketEvent entity representing a significant market event or trend.

    MarketEvents are broader than individual company signals and
    typically affect multiple entities within a market.

    Attributes:
        id: Unique identifier for the market event
        name: Name/title of the market event
        event_type: Type of market event
        description: Detailed description of the event
        impact: Impact level of the event
        duration: Expected duration of the event
        affected_markets: Markets affected by this event
        affected_companies: Companies directly affected
        related_technologies: Technologies involved
        start_date: When the event began
        end_date: When the event is expected to end (if known)
        is_ongoing: Whether the event is still ongoing
        confidence: Confidence in the event assessment
        source: Source of the event information
        source_urls: URLs for source information
        tags: Tags for categorization
        metadata: Additional event-specific data
        related_events: IDs of related market events
        opportunities: Identified opportunities from this event
        threats: Identified threats from this event
        created_at: When this event was created
        updated_at: When this event was last updated
    """

    id: EntityId
    name: str
    event_type: MarketEventType
    description: str
    impact: MarketEventImpact = MarketEventImpact.MODERATE
    duration: MarketEventDuration = MarketEventDuration.UNKNOWN
    affected_markets: Set[str] = field(default_factory=set)
    affected_companies: Set[EntityId] = field(default_factory=set)
    related_technologies: Set[str] = field(default_factory=set)
    start_date: Optional[Timestamp] = None
    end_date: Optional[Timestamp] = None
    is_ongoing: bool = True
    confidence: Confidence = field(default_factory=lambda: Confidence.medium())
    source: Optional[str] = None
    source_urls: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_events: Set[EntityId] = field(default_factory=set)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    created_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    updated_at: Timestamp = field(default_factory=lambda: Timestamp.now())

    def __post_init__(self) -> None:
        """Validate the market event entity."""
        if not self.name or not self.name.strip():
            raise ValueError("Market event name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Market event description cannot be empty")

    @property
    def is_high_impact(self) -> bool:
        """Check if event has high or higher impact."""
        return self.impact in {
            MarketEventImpact.SIGNIFICANT,
            MarketEventImpact.MAJOR,
            MarketEventImpact.TRANSFORMATIONAL,
        }

    @property
    def is_transient(self) -> bool:
        """Check if event is expected to be short-lived."""
        return self.duration in {MarketEventDuration.ONE_TIME, MarketEventDuration.SHORT_TERM}

    @property
    def days_since_start(self) -> Optional[int]:
        """Calculate days since event started."""
        if self.start_date is None:
            return None
        return (Timestamp.now() - self.start_date).days

    @property
    def days_until_end(self) -> Optional[int]:
        """Calculate days until event ends."""
        if self.end_date is None:
            return None
        delta = self.end_date - Timestamp.now()
        return delta.days

    @property
    def is_expired(self) -> bool:
        """Check if event has ended."""
        if self.is_ongoing and self.end_date:
            return Timestamp.now() > self.end_date
        return False

    @property
    def opportunity_count(self) -> int:
        """Number of identified opportunities."""
        return len(self.opportunities)

    @property
    def threat_count(self) -> int:
        """Number of identified threats."""
        return len(self.threats)

    def mark_ended(self, end_date: Optional[Timestamp] = None) -> "MarketEvent":
        """Mark event as ended."""
        return MarketEvent(
            id=self.id,
            name=self.name,
            event_type=self.event_type,
            description=self.description,
            impact=self.impact,
            duration=self.duration,
            affected_markets=self.affected_markets,
            affected_companies=self.affected_companies,
            related_technologies=self.related_technologies,
            start_date=self.start_date,
            end_date=end_date or Timestamp.now(),
            is_ongoing=False,
            confidence=self.confidence,
            source=self.source,
            source_urls=self.source_urls,
            tags=self.tags,
            metadata=self.metadata,
            related_events=self.related_events,
            opportunities=self.opportunities,
            threats=self.threats,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    def add_company(self, company_id: EntityId) -> "MarketEvent":
        """Add an affected company."""
        return MarketEvent(
            id=self.id,
            name=self.name,
            event_type=self.event_type,
            description=self.description,
            impact=self.impact,
            duration=self.duration,
            affected_markets=self.affected_markets,
            affected_companies=self.affected_companies | {company_id},
            related_technologies=self.related_technologies,
            start_date=self.start_date,
            end_date=self.end_date,
            is_ongoing=self.is_ongoing,
            confidence=self.confidence,
            source=self.source,
            source_urls=self.source_urls,
            tags=self.tags,
            metadata=self.metadata,
            related_events=self.related_events,
            opportunities=self.opportunities,
            threats=self.threats,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    def add_opportunity(self, opportunity: str) -> "MarketEvent":
        """Add an identified opportunity."""
        return MarketEvent(
            id=self.id,
            name=self.name,
            event_type=self.event_type,
            description=self.description,
            impact=self.impact,
            duration=self.duration,
            affected_markets=self.affected_markets,
            affected_companies=self.affected_companies,
            related_technologies=self.related_technologies,
            start_date=self.start_date,
            end_date=self.end_date,
            is_ongoing=self.is_ongoing,
            confidence=self.confidence,
            source=self.source,
            source_urls=self.source_urls,
            tags=self.tags,
            metadata=self.metadata,
            related_events=self.related_events,
            opportunities=self.opportunities + [opportunity],
            threats=self.threats,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    def add_threat(self, threat: str) -> "MarketEvent":
        """Add an identified threat."""
        return MarketEvent(
            id=self.id,
            name=self.name,
            event_type=self.event_type,
            description=self.description,
            impact=self.impact,
            duration=self.duration,
            affected_markets=self.affected_markets,
            affected_companies=self.affected_companies,
            related_technologies=self.related_technologies,
            start_date=self.start_date,
            end_date=self.end_date,
            is_ongoing=self.is_ongoing,
            confidence=self.confidence,
            source=self.source,
            source_urls=self.source_urls,
            tags=self.tags,
            metadata=self.metadata,
            related_events=self.related_events,
            opportunities=self.opportunities,
            threats=self.threats + [threat],
            created_at=self.created_at,
            updated_at=Timestamp.now(),
        )

    @classmethod
    def create(
        cls,
        name: str,
        event_type: MarketEventType,
        description: str,
    ) -> "MarketEvent":
        """Factory method to create a new MarketEvent."""
        return cls(
            id=EntityId.generate(),
            name=name,
            event_type=event_type,
            description=description,
        )


__all__ = [
    "MarketEvent",
    "MarketEventType",
    "MarketEventImpact",
    "MarketEventDuration",
]