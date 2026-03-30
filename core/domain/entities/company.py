"""
Company Entity

Represents a company in the competitive intelligence system.
This is a domain entity with no external dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Set
from enum import Enum

from ..value_objects.entity_id import EntityId
from ..value_objects.money import Money
from ..value_objects.confidence import Confidence
from ..value_objects.timestamp import Timestamp


class CompanyStatus(Enum):
    """Company operational status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ACQUIRED = "acquired"
    BANKRUPT = "bankrupt"
    UNKNOWN = "unknown"


class CompanyStage(Enum):
    """Company development stage."""
    IDEA = "idea"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    IPO = "ipo"
    PUBLIC = "public"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Company:
    """
    Company entity representing a business in the competitive landscape.

    This entity follows the Value Object pattern for immutable data
    and Entity pattern for identity-based equality.

    Attributes:
        id: Unique identifier for the company
        name: Legal name of the company
        domain: Primary domain/website
        status: Current operational status
        stage: Development stage (if startup)
        founded_at: When the company was founded
        description: Brief description of the company
        headquarters: Location of company headquarters
        employees: Estimated number of employees
        funding: Total funding raised
        last_funding_round: Details of last funding round
        markets: Market segments the company operates in
        technologies: Technologies used by the company
        competitors: Known competitor company IDs
        confidence: Confidence level of the data
        created_at: When this entity was created
        updated_at: When this entity was last updated
        source: Source of the information
    """

    id: EntityId
    name: str
    domain: Optional[str] = None
    status: CompanyStatus = CompanyStatus.UNKNOWN
    stage: CompanyStage = CompanyStage.UNKNOWN
    founded_at: Optional[Timestamp] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    employees: Optional[int] = None
    funding: Optional[Money] = None
    last_funding_round: Optional[str] = None
    markets: Set[str] = field(default_factory=set)
    technologies: Set[str] = field(default_factory=set)
    competitors: Set[EntityId] = field(default_factory=set)
    confidence: Confidence = field(default_factory=lambda: Confidence.medium())
    created_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    updated_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    source: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate the company entity."""
        if not self.name or not self.name.strip():
            raise ValueError("Company name cannot be empty")
        if self.employees is not None and self.employees < 0:
            raise ValueError("Number of employees cannot be negative")

    @property
    def is_startup(self) -> bool:
        """Check if this is a startup based on stage."""
        return self.stage in {
            CompanyStage.IDEA,
            CompanyStage.PRE_SEED,
            CompanyStage.SEED,
            CompanyStage.SERIES_A,
            CompanyStage.SERIES_B,
            CompanyStage.SERIES_C,
            CompanyStage.SERIES_D,
        }

    @property
    def is_public(self) -> bool:
        """Check if the company is publicly traded."""
        return self.stage in {CompanyStage.IPO, CompanyStage.PUBLIC}

    @property
    def years_since_founded(self) -> Optional[int]:
        """Calculate years since founding."""
        if self.founded_at is None:
            return None
        return Timestamp.now().year - self.founded_at.year

    @property
    def primary_market(self) -> Optional[str]:
        """Get the first/primary market if available."""
        return next(iter(self.markets)) if self.markets else None

    def add_competitor(self, competitor_id: EntityId) -> "Company":
        """Add a competitor and return a new Company instance."""
        return Company(
            id=self.id,
            name=self.name,
            domain=self.domain,
            status=self.status,
            stage=self.stage,
            founded_at=self.founded_at,
            description=self.description,
            headquarters=self.headquarters,
            employees=self.employees,
            funding=self.funding,
            last_funding_round=self.last_funding_round,
            markets=self.markets,
            technologies=self.technologies,
            competitors=self.competitors | {competitor_id},
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            source=self.source,
        )

    def update_funding(self, new_funding: Money) -> "Company":
        """Update funding information and return a new Company instance."""
        return Company(
            id=self.id,
            name=self.name,
            domain=self.domain,
            status=self.status,
            stage=self.stage,
            founded_at=self.founded_at,
            description=self.description,
            headquarters=self.headquarters,
            employees=self.employees,
            funding=new_funding,
            last_funding_round=self.last_funding_round,
            markets=self.markets,
            technologies=self.technologies,
            competitors=self.competitors,
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            source=self.source,
        )

    def with_status(self, status: CompanyStatus) -> "Company":
        """Return a new Company instance with updated status."""
        return Company(
            id=self.id,
            name=self.name,
            domain=self.domain,
            status=status,
            stage=self.stage,
            founded_at=self.founded_at,
            description=self.description,
            headquarters=self.headquarters,
            employees=self.employees,
            funding=self.funding,
            last_funding_round=self.last_funding_round,
            markets=self.markets,
            technologies=self.technologies,
            competitors=self.competitors,
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=Timestamp.now(),
            source=self.source,
        )

    @classmethod
    def create(
        cls,
        name: str,
        domain: Optional[str] = None,
    ) -> "Company":
        """Factory method to create a new Company."""
        return cls(
            id=EntityId.generate(),
            name=name,
            domain=domain,
        )


@dataclass(frozen=True)
class CompanySnapshot:
    """
    Snapshot of a company at a point in time for historical tracking.

    Used for tracking company changes over time.
    """

    company_id: EntityId
    name: str
    domain: Optional[str]
    status: CompanyStatus
    stage: CompanyStage
    employees: Optional[int]
    funding: Optional[Money]
    captured_at: Timestamp = field(default_factory=lambda: Timestamp.now())
    source: Optional[str] = None


__all__ = [
    "Company",
    "CompanyStatus",
    "CompanyStage",
    "CompanySnapshot",
]