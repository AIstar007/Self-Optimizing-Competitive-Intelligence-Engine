"""
Domain Repository Interfaces

These interfaces define the contract for data persistence.
The infrastructure layer implements these interfaces.

Following Dependency Inversion Principle - the domain layer
does not depend on infrastructure, infrastructure depends
on these domain interfaces.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Set, Dict, Any
from datetime import datetime

from ..entities.company import Company, CompanyStatus, CompanyStage, CompanySnapshot
from ..entities.signal import Signal, SignalType, SignalSeverity, SignalSource, SignalPattern
from ..entities.report import Report, ReportType, ReportStatus, ReportFormat
from ..entities.market_event import MarketEvent, MarketEventType, MarketEventImpact
from ..entities.agent_policy import AgentPolicy, PolicyType, PolicyStatus
from ..value_objects.entity_id import EntityId
from ..value_objects.timestamp import Timestamp
from ..value_objects.confidence import Confidence


# ============================================================================
# Company Repository Interface
# ============================================================================


class CompanyRepository(ABC):
    """
    Repository interface for Company entities.

    Defines the contract for persisting and retrieving
    company information from storage.
    """

    @abstractmethod
    async def save(self, company: Company) -> Company:
        """Save a company entity. Returns the saved entity."""
        pass

    @abstractmethod
    async def find_by_id(self, company_id: EntityId) -> Optional[Company]:
        """Find a company by its ID."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Company]:
        """Find a company by name (exact match)."""
        pass

    @abstractmethod
    async def find_by_domain(self, domain: str) -> Optional[Company]:
        """Find a company by domain."""
        pass

    @abstractmethod
    async def find_by_name_fuzzy(self, name: str, limit: int = 10) -> List[Company]:
        """Find companies with similar names (fuzzy search)."""
        pass

    @abstractmethod
    async def find_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Company]:
        """Find all companies with pagination."""
        pass

    @abstractmethod
    async def find_by_status(
        self,
        status: CompanyStatus,
        limit: Optional[int] = None,
    ) -> List[Company]:
        """Find companies by status."""
        pass

    @abstractmethod
    async def find_by_stage(
        self,
        stage: CompanyStage,
        limit: Optional[int] = None,
    ) -> List[Company]:
        """Find companies by development stage."""
        pass

    @abstractmethod
    async def find_by_market(
        self,
        market: str,
        limit: Optional[int] = None,
    ) -> List[Company]:
        """Find companies operating in a specific market."""
        pass

    @abstractmethod
    async def find_by_technology(
        self,
        technology: str,
        limit: Optional[int] = None,
    ) -> List[Company]:
        """Find companies using a specific technology."""
        pass

    @abstractmethod
    async def find_competitors(self, company_id: EntityId) -> List[Company]:
        """Find all competitors of a company."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[Company]:
        """Search companies with optional filters."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count companies matching filters."""
        pass

    @abstractmethod
    async def exists(self, company_id: EntityId) -> bool:
        """Check if a company exists."""
        pass

    @abstractmethod
    async def delete(self, company_id: EntityId) -> bool:
        """Delete a company. Returns True if deleted."""
        pass

    @abstractmethod
    async def save_snapshot(self, snapshot: CompanySnapshot) -> CompanySnapshot:
        """Save a company snapshot for historical tracking."""
        pass

    @abstractmethod
    async def get_snapshots(
        self,
        company_id: EntityId,
        from_date: Optional[Timestamp] = None,
        to_date: Optional[Timestamp] = None,
        limit: int = 10,
    ) -> List[CompanySnapshot]:
        """Get company snapshots within a date range."""
        pass


# ============================================================================
# Signal Repository Interface
# ============================================================================


class SignalRepository(ABC):
    """
    Repository interface for Signal entities.

    Defines the contract for persisting and retrieving
    intelligence signals.
    """

    @abstractmethod
    async def save(self, signal: Signal) -> Signal:
        """Save a signal entity. Returns the saved entity."""
        pass

    @abstractmethod
    async def find_by_id(self, signal_id: EntityId) -> Optional[Signal]:
        """Find a signal by its ID."""
        pass

    @abstractmethod
    async def find_by_company(
        self,
        company_id: EntityId,
        signal_type: Optional[SignalType] = None,
        limit: Optional[int] = None,
    ) -> List[Signal]:
        """Find signals for a company, optionally filtered by type."""
        pass

    @abstractmethod
    async def find_by_type(
        self,
        signal_type: SignalType,
        limit: Optional[int] = None,
    ) -> List[Signal]:
        """Find signals by type."""
        pass

    @abstractmethod
    async def find_by_severity(
        self,
        severity: SignalSeverity,
        limit: Optional[int] = None,
    ) -> List[Signal]:
        """Find signals by severity level."""
        pass

    @abstractmethod
    async def find_by_source(
        self,
        source: SignalSource,
        limit: Optional[int] = None,
    ) -> List[Signal]:
        """Find signals by source."""
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        from_date: Timestamp,
        to_date: Timestamp,
        limit: Optional[int] = None,
    ) -> List[Signal]:
        """Find signals within a date range."""
        pass

    @abstractmethod
    async def find_recent(
        self,
        hours: int = 24,
        limit: int = 50,
    ) -> List[Signal]:
        """Find recent signals from the last N hours."""
        pass

    @abstractmethod
    async def find_unverified(self, limit: int = 50) -> List[Signal]:
        """Find signals that haven't been verified."""
        pass

    @abstractmethod
    async def find_by_tags(
        self,
        tags: Set[str],
        match_all: bool = False,
        limit: int = 20,
    ) -> List[Signal]:
        """Find signals by tags."""
        pass

    @abstractmethod
    async def find_related(
        self,
        signal_id: EntityId,
        limit: int = 10,
    ) -> List[Signal]:
        """Find signals related to a given signal."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[Signal]:
        """Search signals with optional filters."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count signals matching filters."""
        pass

    @abstractmethod
    async def exists(self, signal_id: EntityId) -> bool:
        """Check if a signal exists."""
        pass

    @abstractmethod
    async def delete(self, signal_id: EntityId) -> bool:
        """Delete a signal. Returns True if deleted."""
        pass

    # Pattern methods
    @abstractmethod
    async def save_pattern(self, pattern: SignalPattern) -> SignalPattern:
        """Save a signal pattern."""
        pass

    @abstractmethod
    async def find_patterns(
        self,
        pattern_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[SignalPattern]:
        """Find signal patterns."""
        pass

    @abstractmethod
    async def find_emerging_patterns(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> List[SignalPattern]:
        """Find patterns that have emerged in the last N days."""
        pass


# ============================================================================
# Report Repository Interface
# ============================================================================


class ReportRepository(ABC):
    """
    Repository interface for Report entities.

    Defines the contract for persisting and retrieving
    intelligence reports.
    """

    @abstractmethod
    async def save(self, report: Report) -> Report:
        """Save a report entity. Returns the saved entity."""
        pass

    @abstractmethod
    async def find_by_id(self, report_id: EntityId) -> Optional[Report]:
        """Find a report by its ID."""
        pass

    @abstractmethod
    async def find_by_type(
        self,
        report_type: ReportType,
        limit: Optional[int] = None,
    ) -> List[Report]:
        """Find reports by type."""
        pass

    @abstractmethod
    async def find_by_status(
        self,
        status: ReportStatus,
        limit: Optional[int] = None,
    ) -> List[Report]:
        """Find reports by status."""
        pass

    @abstractmethod
    async def find_by_format(
        self,
        format: ReportFormat,
        limit: Optional[int] = None,
    ) -> List[Report]:
        """Find reports by format."""
        pass

    @abstractmethod
    async def find_by_company(self, company_id: EntityId) -> List[Report]:
        """Find reports that include a specific company."""
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        from_date: Timestamp,
        to_date: Timestamp,
        limit: Optional[int] = None,
    ) -> List[Report]:
        """Find reports within a date range."""
        pass

    @abstractmethod
    async def find_recent(
        self,
        limit: int = 20,
    ) -> List[Report]:
        """Find recent reports."""
        pass

    @abstractmethod
    async def find_by_requested_by(
        self,
        requested_by: str,
        limit: int = 20,
    ) -> List[Report]:
        """Find reports requested by a specific user or system."""
        pass

    @abstractmethod
    async def find_by_tags(
        self,
        tags: Set[str],
        match_all: bool = False,
        limit: int = 20,
    ) -> List[Report]:
        """Find reports by tags."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[Report]:
        """Search reports with optional filters."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count reports matching filters."""
        pass

    @abstractmethod
    async def exists(self, report_id: EntityId) -> bool:
        """Check if a report exists."""
        pass

    @abstractmethod
    async def delete(self, report_id: EntityId) -> bool:
        """Delete a report. Returns True if deleted."""
        pass


# ============================================================================
# Market Event Repository Interface
# ============================================================================


class MarketEventRepository(ABC):
    """
    Repository interface for MarketEvent entities.

    Defines the contract for persisting and retrieving
    market events.
    """

    @abstractmethod
    async def save(self, event: MarketEvent) -> MarketEvent:
        """Save a market event. Returns the saved event."""
        pass

    @abstractmethod
    async def find_by_id(self, event_id: EntityId) -> Optional[MarketEvent]:
        """Find a market event by its ID."""
        pass

    @abstractmethod
    async def find_by_type(
        self,
        event_type: MarketEventType,
        limit: Optional[int] = None,
    ) -> List[MarketEvent]:
        """Find market events by type."""
        pass

    @abstractmethod
    async def find_by_impact(
        self,
        impact: MarketEventImpact,
        limit: Optional[int] = None,
    ) -> List[MarketEvent]:
        """Find market events by impact level."""
        pass

    @abstractmethod
    async def find_ongoing(
        self,
        limit: Optional[int] = None,
    ) -> List[MarketEvent]:
        """Find currently ongoing market events."""
        pass

    @abstractmethod
    async def find_by_market(
        self,
        market: str,
        limit: Optional[int] = None,
    ) -> List[MarketEvent]:
        """Find market events affecting a specific market."""
        pass

    @abstractmethod
    async def find_by_company(self, company_id: EntityId) -> List[MarketEvent]:
        """Find market events affecting a specific company."""
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        from_date: Timestamp,
        to_date: Timestamp,
        limit: Optional[int] = None,
    ) -> List[MarketEvent]:
        """Find market events within a date range."""
        pass

    @abstractmethod
    async def find_recent(
        self,
        limit: int = 20,
    ) -> List[MarketEvent]:
        """Find recent market events."""
        pass

    @abstractmethod
    async def find_high_impact(
        self,
        limit: int = 20,
    ) -> List[MarketEvent]:
        """Find market events with high or higher impact."""
        pass

    @abstractmethod
    async def find_related(
        self,
        event_id: EntityId,
        limit: int = 10,
    ) -> List[MarketEvent]:
        """Find related market events."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[MarketEvent]:
        """Search market events with optional filters."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count market events matching filters."""
        pass

    @abstractmethod
    async def exists(self, event_id: EntityId) -> bool:
        """Check if a market event exists."""
        pass

    @abstractmethod
    async def delete(self, event_id: EntityId) -> bool:
        """Delete a market event. Returns True if deleted."""
        pass


# ============================================================================
# Agent Policy Repository Interface
# ============================================================================


class AgentPolicyRepository(ABC):
    """
    Repository interface for AgentPolicy entities.

    Defines the contract for persisting and retrieving
    agent learning policies.
    """

    @abstractmethod
    async def save(self, policy: AgentPolicy) -> AgentPolicy:
        """Save an agent policy. Returns the saved policy."""
        pass

    @abstractmethod
    async def find_by_id(self, policy_id: EntityId) -> Optional[AgentPolicy]:
        """Find a policy by its ID."""
        pass

    @abstractmethod
    async def find_by_agent(
        self,
        agent_id: str,
        policy_type: Optional[PolicyType] = None,
    ) -> List[AgentPolicy]:
        """Find policies for a specific agent."""
        pass

    @abstractmethod
    async def find_by_agent_type(
        self,
        agent_type: str,
        policy_type: Optional[PolicyType] = None,
    ) -> List[AgentPolicy]:
        """Find policies for agents of a specific type."""
        pass

    @abstractmethod
    async def find_by_type(
        self,
        policy_type: PolicyType,
        limit: Optional[int] = None,
    ) -> List[AgentPolicy]:
        """Find policies by type."""
        pass

    @abstractmethod
    async def find_by_status(
        self,
        status: PolicyStatus,
        limit: Optional[int] = None,
    ) -> List[AgentPolicy]:
        """Find policies by status."""
        pass

    @abstractmethod
    async def find_active_policies(
        self,
        agent_id: Optional[str] = None,
    ) -> List[AgentPolicy]:
        """Find all active policies, optionally filtered by agent."""
        pass

    @abstractmethod
    async def find_effective_policies(
        self,
        min_effectiveness: int = 70,
        limit: int = 20,
    ) -> List[AgentPolicy]:
        """Find policies with effectiveness above threshold."""
        pass

    @abstractmethod
    async def find_most_used(
        self,
        limit: int = 20,
    ) -> List[AgentPolicy]:
        """Find policies ordered by usage count."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[AgentPolicy]:
        """Search policies with optional filters."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count policies matching filters."""
        pass

    @abstractmethod
    async def exists(self, policy_id: EntityId) -> bool:
        """Check if a policy exists."""
        pass

    @abstractmethod
    async def delete(self, policy_id: EntityId) -> bool:
        """Delete a policy. Returns True if deleted."""
        pass


# ============================================================================
# Knowledge Graph Repository Interface
# ============================================================================


class KnowledgeGraphRepository(ABC):
    """
    Repository interface for Knowledge Graph operations.

    Defines the contract for managing the graph-based
    knowledge representation of entities and relationships.
    """

    @abstractmethod
    async def add_node(
        self,
        node_id: str,
        node_type: str,
        properties: Dict[str, Any],
    ) -> None:
        """Add a node to the knowledge graph."""
        pass

    @abstractmethod
    async def add_edge(
        self,
        from_node: str,
        to_node: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an edge to the knowledge graph."""
        pass

    @abstractmethod
    async def get_node(
        self,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a node by its ID."""
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get neighboring nodes of a node."""
        pass

    @abstractmethod
    async def get_connected_nodes(
        self,
        node_id: str,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Get all nodes connected within max_depth hops."""
        pass

    @abstractmethod
    async def find_path(
        self,
        from_node: str,
        to_node: str,
        max_length: int = 5,
    ) -> Optional[List[str]]:
        """Find shortest path between two nodes. Returns node IDs."""
        pass

    @abstractmethod
    async def find_shortest_paths(
        self,
        from_node: str,
        to_node: str,
        max_length: int = 5,
        limit: int = 5,
    ) -> List[List[str]]:
        """Find multiple shortest paths between two nodes."""
        pass

    @abstractmethod
    async def find_by_type(
        self,
        node_type: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find all nodes of a specific type."""
        pass

    @abstractmethod
    async def find_by_property(
        self,
        property_name: str,
        property_value: Any,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find nodes by property value."""
        pass

    @abstractmethod
    async def search_nodes(
        self,
        query: str,
        node_types: Optional[Set[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search nodes by text query."""
        pass

    @abstractmethod
    async def get_subgraph(
        self,
        center_nodes: Set[str],
        radius: int = 2,
    ) -> Dict[str, Any]:
        """Get a subgraph centered on specified nodes."""
        pass

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges. Returns True if deleted."""
        pass

    @abstractmethod
    async def delete_edge(
        self,
        from_node: str,
        to_node: str,
        edge_type: Optional[str] = None,
    ) -> bool:
        """Delete an edge. Returns True if deleted."""
        pass

    @abstractmethod
    async def update_node(
        self,
        node_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        """Update node properties. Returns True if updated."""
        pass


# ============================================================================
# Export all repository interfaces
# ============================================================================


__all__ = [
    "CompanyRepository",
    "SignalRepository",
    "ReportRepository",
    "MarketEventRepository",
    "AgentPolicyRepository",
    "KnowledgeGraphRepository",
]