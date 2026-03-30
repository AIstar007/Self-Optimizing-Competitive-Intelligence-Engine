"""
SQLAlchemy ORM models for all domain entities.

This module defines the database schema using SQLAlchemy models that map to domain entities.
All models are designed for async operations and follow best practices for database schema design.

Models:
    - CompanyModel: Company entity with funding and status
    - SignalModel: Competitive intelligence signals with patterns
    - ReportModel: Generated intelligence reports with sections
    - MarketEventModel: Market-level events affecting entities
    - AgentPolicyModel: Learned agent policies and feedback
    - KnowledgeNodeModel: Knowledge graph nodes
    - KnowledgeEdgeModel: Knowledge graph edges and relationships
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    JSON,
    DECIMAL,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.domain.entities import (
    CompanyStatus,
    CompanyStage,
    SignalType,
    SignalSeverity,
    SignalSource,
    ReportType,
    ReportStatus,
    ReportFormat,
    MarketEventType,
    MarketEventImpact,
    MarketEventDuration,
    PolicyType,
    PolicyStatus,
    PolicySource,
)
from core.infrastructure.database import Base


class CompanyModel(Base):
    """SQLAlchemy model for Company entity."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[CompanyStatus] = mapped_column(Enum(CompanyStatus), default=CompanyStatus.ACTIVE)
    stage: Mapped[CompanyStage] = mapped_column(Enum(CompanyStage), default=CompanyStage.IDEA)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    headquarters: Mapped[Optional[str]] = mapped_column(String(255))
    employees: Mapped[Optional[int]] = mapped_column(Integer)
    total_funding_cents: Mapped[Optional[int]] = mapped_column(Integer)  # Store as cents
    funding_currency: Mapped[str] = mapped_column(String(3), default="USD")
    primary_market: Mapped[Optional[str]] = mapped_column(String(255))
    markets: Mapped[list[str]] = mapped_column(JSON, default=list)
    technologies: Mapped[list[str]] = mapped_column(JSON, default=list)
    competitors: Mapped[list[str]] = mapped_column(JSON, default=list)  # List of company IDs
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    signals: Mapped[list["SignalModel"]] = relationship("SignalModel", back_populates="company")
    market_events: Mapped[list["MarketEventModel"]] = relationship(
        "MarketEventModel", back_populates="companies", secondary="market_event_companies"
    )

    __table_args__ = (
        UniqueConstraint("name", "domain", name="uq_company_name_domain"),
        Index("ix_company_status", "status"),
        Index("ix_company_stage", "stage"),
        Index("ix_company_created_at", "created_at"),
    )


class SignalModel(Base):
    """SQLAlchemy model for Signal entity."""

    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), index=True)
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType), nullable=False)
    severity: Mapped[SignalSeverity] = mapped_column(Enum(SignalSeverity), default=SignalSeverity.MEDIUM)
    source: Mapped[SignalSource] = mapped_column(Enum(SignalSource), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(2048))
    impact_score: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_signal_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    company: Mapped["CompanyModel"] = relationship("CompanyModel", back_populates="signals")

    __table_args__ = (
        Index("ix_signal_company_id", "company_id"),
        Index("ix_signal_type", "signal_type"),
        Index("ix_signal_severity", "severity"),
        Index("ix_signal_source", "source"),
        Index("ix_signal_detected_at", "detected_at"),
        Index("ix_signal_is_verified", "is_verified"),
    )


class ReportModel(Base):
    """SQLAlchemy model for Report entity."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.DRAFT)
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat), default=ReportFormat.MARKDOWN)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(2048))
    company_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    signal_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    sections: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    requested_by: Mapped[Optional[str]] = mapped_column(String(255))
    generated_by: Mapped[Optional[str]] = mapped_column(String(255))
    generation_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_report_type", "report_type"),
        Index("ix_report_status", "status"),
        Index("ix_report_format", "format"),
        Index("ix_report_created_at", "created_at"),
    )


class MarketEventModel(Base):
    """SQLAlchemy model for MarketEvent entity."""

    __tablename__ = "market_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[MarketEventType] = mapped_column(Enum(MarketEventType), nullable=False)
    impact: Mapped[MarketEventImpact] = mapped_column(Enum(MarketEventImpact), default=MarketEventImpact.MODERATE)
    duration: Mapped[MarketEventDuration] = mapped_column(
        Enum(MarketEventDuration), default=MarketEventDuration.TEMPORARY
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(255))
    affected_company_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    opportunities: Mapped[list[str]] = mapped_column(JSON, default=list)
    threats: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_market_event_type", "event_type"),
        Index("ix_market_event_impact", "impact"),
        Index("ix_market_event_market", "market"),
        Index("ix_market_event_started_at", "started_at"),
    )


class AgentPolicyModel(Base):
    """SQLAlchemy model for AgentPolicy entity."""

    __tablename__ = "agent_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    policy_type: Mapped[PolicyType] = mapped_column(Enum(PolicyType), nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus), default=PolicyStatus.DRAFT)
    source: Mapped[PolicySource] = mapped_column(Enum(PolicySource), default=PolicySource.MANUAL)
    description: Mapped[Optional[str]] = mapped_column(Text)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    tool_preferences: Mapped[list[dict]] = mapped_column(JSON, default=list)
    strategies: Mapped[list[dict]] = mapped_column(JSON, default=list)
    failed_approaches: Mapped[list[dict]] = mapped_column(JSON, default=list)
    feedback: Mapped[list[dict]] = mapped_column(JSON, default=list)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_policy_agent_id", "agent_id"),
        Index("ix_policy_agent_type", "agent_type"),
        Index("ix_policy_type", "policy_type"),
        Index("ix_policy_status", "status"),
    )


class KnowledgeNodeModel(Base):
    """SQLAlchemy model for knowledge graph nodes."""

    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    node_label: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[Optional[list[float]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_knowledge_node_type", "node_type"),
        Index("ix_knowledge_node_entity_id", "entity_id"),
    )


class KnowledgeEdgeModel(Base):
    """SQLAlchemy model for knowledge graph edges."""

    __tablename__ = "knowledge_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id"), index=True)
    target_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_knowledge_edge_source", "source_node_id"),
        Index("ix_knowledge_edge_target", "target_node_id"),
        Index("ix_knowledge_edge_relationship", "relationship_type"),
    )


# Junction table for many-to-many relationship between MarketEvents and Companies
market_event_companies = Base.metadata.create_table(
    "market_event_companies",
    Column("market_event_id", String(36), ForeignKey("market_events.id"), primary_key=True),
    Column("company_id", String(36), ForeignKey("companies.id"), primary_key=True),
    extend_existing=True,
)


__all__ = [
    "CompanyModel",
    "SignalModel",
    "ReportModel",
    "MarketEventModel",
    "AgentPolicyModel",
    "KnowledgeNodeModel",
    "KnowledgeEdgeModel",
    "market_event_companies",
]
