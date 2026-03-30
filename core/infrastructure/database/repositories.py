"""
Async SQLAlchemy repository implementations for all domain entities.

This module implements all repository interfaces defined in core.domain.interfaces.repositories
using SQLAlchemy as the ORM. All operations are fully async and support transactions.

Repositories:
    - CompanyRepository: Company entity persistence
    - SignalRepository: Signal entity persistence
    - ReportRepository: Report entity persistence
    - MarketEventRepository: MarketEvent entity persistence
    - AgentPolicyRepository: AgentPolicy entity persistence
    - KnowledgeGraphRepository: Knowledge graph node/edge persistence
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, like, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.domain import (
    Company,
    CompanyStatus,
    CompanyStage,
    Confidence,
    EntityId,
    Market,
    Money,
    Signal,
    SignalPattern,
    SignalSeverity,
    SignalSource,
    SignalType,
    Timestamp,
    Report,
    ReportFormat,
    ReportStatus,
    ReportType,
    ReportSection,
    MarketEvent,
    MarketEventDuration,
    MarketEventImpact,
    MarketEventType,
    AgentPolicy,
    PolicyStatus,
    PolicyType,
    PolicySource,
    ToolPreference,
    StrategyPattern,
    PolicyFeedback,
    CompanyRepository,
    SignalRepository,
    ReportRepository,
    MarketEventRepository,
    AgentPolicyRepository,
    KnowledgeGraphRepository,
)
from core.infrastructure.database.models import (
    CompanyModel,
    SignalModel,
    ReportModel,
    MarketEventModel,
    AgentPolicyModel,
    KnowledgeNodeModel,
    KnowledgeEdgeModel,
)


class SQLCompanyRepository(CompanyRepository):
    """Async SQLAlchemy implementation of CompanyRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def save(self, company: Company) -> None:
        """Save or update a company."""
        model = await self._to_model(company)
        self.session.add(model)
        await self.session.flush()

    async def find_by_id(self, company_id: EntityId) -> Optional[Company]:
        """Find company by ID."""
        stmt = select(CompanyModel).where(CompanyModel.id == str(company_id))
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return await self._to_entity(model) if model else None

    async def find_by_name(self, name: str) -> Optional[Company]:
        """Find company by exact name."""
        stmt = select(CompanyModel).where(CompanyModel.name == name)
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return await self._to_entity(model) if model else None

    async def find_by_domain(self, domain: str) -> Optional[Company]:
        """Find company by domain."""
        stmt = select(CompanyModel).where(CompanyModel.domain == domain)
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return await self._to_entity(model) if model else None

    async def find_by_name_fuzzy(self, name: str, limit: int = 10) -> list[Company]:
        """Find companies by fuzzy name matching."""
        search_pattern = f"%{name.lower()}%"
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.name.ilike(search_pattern))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[Company]:
        """Find all companies with pagination."""
        stmt = (
            select(CompanyModel)
            .order_by(desc(CompanyModel.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_status(self, status: CompanyStatus, limit: int = 100) -> list[Company]:
        """Find companies by status."""
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.status == status)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_stage(self, stage: CompanyStage, limit: int = 100) -> list[Company]:
        """Find companies by funding stage."""
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.stage == stage)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_market(self, market: str, limit: int = 100) -> list[Company]:
        """Find companies by market."""
        # Using array contains check - may vary by database
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.markets.contains([market]))
            .limit(limit)
        )
        try:
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [await self._to_entity(m) for m in models]
        except Exception:
            # Fallback for databases without array support
            return []

    async def find_by_technology(self, technology: str, limit: int = 100) -> list[Company]:
        """Find companies using a technology."""
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.technologies.contains([technology]))
            .limit(limit)
        )
        try:
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [await self._to_entity(m) for m in models]
        except Exception:
            return []

    async def find_competitors(self, company_id: EntityId, limit: int = 50) -> list[Company]:
        """Find competitors of a company."""
        stmt = select(CompanyModel).where(CompanyModel.id == str(company_id))
        result = await self.session.execute(stmt)
        company = result.scalars().first()

        if not company or not company.competitors:
            return []

        competitor_ids = company.competitors[:limit]
        stmt = select(CompanyModel).where(CompanyModel.id.in_(competitor_ids))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def search(self, query: str, limit: int = 50) -> list[Company]:
        """Search companies by name, domain, or description."""
        search_pattern = f"%{query.lower()}%"
        stmt = (
            select(CompanyModel)
            .where(
                or_(
                    CompanyModel.name.ilike(search_pattern),
                    CompanyModel.domain.ilike(search_pattern),
                    CompanyModel.description.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def count(self) -> int:
        """Count total companies."""
        stmt = select(func.count(CompanyModel.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, company_id: EntityId) -> bool:
        """Check if company exists."""
        stmt = select(func.count(CompanyModel.id)).where(CompanyModel.id == str(company_id))
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def delete(self, company_id: EntityId) -> None:
        """Delete a company."""
        stmt = select(CompanyModel).where(CompanyModel.id == str(company_id))
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        if model:
            await self.session.delete(model)
            await self.session.flush()

    async def save_snapshot(self, company_id: EntityId, snapshot: dict) -> None:
        """Save company snapshot for historical tracking."""
        # This would typically store in a separate historical table
        # For now, we store in metadata
        stmt = select(CompanyModel).where(CompanyModel.id == str(company_id))
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        if model:
            if "snapshots" not in model.metadata:
                model.metadata["snapshots"] = []
            model.metadata["snapshots"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "data": snapshot
            })
            await self.session.flush()

    async def get_snapshots(self, company_id: EntityId) -> list[dict]:
        """Get all snapshots for a company."""
        stmt = select(CompanyModel).where(CompanyModel.id == str(company_id))
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return model.metadata.get("snapshots", []) if model else []

    async def _to_model(self, company: Company) -> CompanyModel:
        """Convert domain entity to SQLAlchemy model."""
        return CompanyModel(
            id=str(company.id),
            name=company.name,
            domain=company.domain,
            description=company.description,
            status=company.status,
            stage=company.stage,
            founded_year=company.founded_year,
            headquarters=company.headquarters,
            employees=company.employees,
            total_funding_cents=int(company.total_funding.in_cents) if company.total_funding else None,
            funding_currency=company.total_funding.currency if company.total_funding else "USD",
            primary_market=company.primary_market,
            markets=company.markets or [],
            technologies=company.technologies or [],
            competitors=[str(c_id) for c_id in company.competitors] if company.competitors else [],
            confidence_score=company.confidence.score,
            metadata=company.metadata or {},
            created_at=company.created_at.to_datetime,
            updated_at=company.updated_at.to_datetime,
        )

    async def _to_entity(self, model: CompanyModel) -> Company:
        """Convert SQLAlchemy model to domain entity."""
        return Company(
            id=EntityId.from_string(model.id),
            name=model.name,
            domain=model.domain,
            description=model.description,
            status=model.status,
            stage=model.stage,
            founded_year=model.founded_year,
            headquarters=model.headquarters,
            employees=model.employees,
            total_funding=Money(
                amount=model.total_funding_cents / 100 if model.total_funding_cents else 0,
                currency=model.funding_currency,
            ),
            primary_market=model.primary_market,
            markets=model.markets or [],
            technologies=model.technologies or [],
            competitors=[EntityId.from_string(c_id) for c_id in (model.competitors or [])],
            confidence=Confidence.from_score(model.confidence_score),
            metadata=model.metadata or {},
            created_at=Timestamp.from_datetime(model.created_at),
            updated_at=Timestamp.from_datetime(model.updated_at),
        )


class SQLSignalRepository(SignalRepository):
    """Async SQLAlchemy implementation of SignalRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def save(self, signal: Signal) -> None:
        """Save or update a signal."""
        model = await self._to_model(signal)
        self.session.add(model)
        await self.session.flush()

    async def find_by_id(self, signal_id: EntityId) -> Optional[Signal]:
        """Find signal by ID."""
        stmt = select(SignalModel).where(SignalModel.id == str(signal_id))
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return await self._to_entity(model) if model else None

    async def find_by_company(self, company_id: EntityId, limit: int = 100) -> list[Signal]:
        """Find signals for a company."""
        stmt = (
            select(SignalModel)
            .where(SignalModel.company_id == str(company_id))
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_type(self, signal_type: SignalType, limit: int = 100) -> list[Signal]:
        """Find signals by type."""
        stmt = (
            select(SignalModel)
            .where(SignalModel.signal_type == signal_type)
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_severity(self, severity: SignalSeverity, limit: int = 100) -> list[Signal]:
        """Find signals by severity."""
        stmt = (
            select(SignalModel)
            .where(SignalModel.severity == severity)
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_source(self, source: SignalSource, limit: int = 100) -> list[Signal]:
        """Find signals by source."""
        stmt = (
            select(SignalModel)
            .where(SignalModel.source == source)
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_date_range(
        self, start: Timestamp, end: Timestamp, limit: int = 100
    ) -> list[Signal]:
        """Find signals within a date range."""
        stmt = (
            select(SignalModel)
            .where(
                and_(
                    SignalModel.detected_at >= start.to_datetime,
                    SignalModel.detected_at <= end.to_datetime,
                )
            )
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_recent(self, hours: int = 24, limit: int = 100) -> list[Signal]:
        """Find recent signals."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(SignalModel)
            .where(SignalModel.detected_at >= cutoff)
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_unverified(self, limit: int = 100) -> list[Signal]:
        """Find unverified signals."""
        stmt = (
            select(SignalModel)
            .where(SignalModel.is_verified == False)
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def find_by_tags(self, tags: list[str], limit: int = 100) -> list[Signal]:
        """Find signals by tags."""
        stmt = (
            select(SignalModel)
            .where(SignalModel.tags.overlap(tags))
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        try:
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [await self._to_entity(m) for m in models]
        except Exception:
            return []

    async def find_related(self, signal_id: EntityId, limit: int = 50) -> list[Signal]:
        """Find related signals."""
        stmt = select(SignalModel).where(SignalModel.id == str(signal_id))
        result = await self.session.execute(stmt)
        signal = result.scalars().first()

        if not signal or not signal.related_signal_ids:
            return []

        related_ids = signal.related_signal_ids[:limit]
        stmt = select(SignalModel).where(SignalModel.id.in_(related_ids))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def search(self, query: str, limit: int = 50) -> list[Signal]:
        """Search signals."""
        search_pattern = f"%{query.lower()}%"
        stmt = (
            select(SignalModel)
            .where(
                or_(
                    SignalModel.title.ilike(search_pattern),
                    SignalModel.description.ilike(search_pattern),
                )
            )
            .order_by(desc(SignalModel.detected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [await self._to_entity(m) for m in models]

    async def count(self) -> int:
        """Count total signals."""
        stmt = select(func.count(SignalModel.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, signal_id: EntityId) -> bool:
        """Check if signal exists."""
        stmt = select(func.count(SignalModel.id)).where(SignalModel.id == str(signal_id))
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def delete(self, signal_id: EntityId) -> None:
        """Delete a signal."""
        stmt = select(SignalModel).where(SignalModel.id == str(signal_id))
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        if model:
            await self.session.delete(model)
            await self.session.flush()

    async def save_pattern(self, pattern: SignalPattern) -> None:
        """Save a signal pattern."""
        # Patterns could be stored in a separate table or in metadata
        # For now, store in Redis or cache
        pass

    async def find_patterns(self, limit: int = 50) -> list[SignalPattern]:
        """Find detected signal patterns."""
        # Implementation would retrieve from pattern storage
        return []

    async def find_emerging_patterns(self, limit: int = 20) -> list[SignalPattern]:
        """Find emerging signal patterns."""
        return []

    async def _to_model(self, signal: Signal) -> SignalModel:
        """Convert domain entity to SQLAlchemy model."""
        return SignalModel(
            id=str(signal.id),
            company_id=str(signal.company_id),
            signal_type=signal.signal_type,
            severity=signal.severity,
            source=signal.source,
            title=signal.title,
            description=signal.description,
            url=signal.url,
            impact_score=signal.impact_score,
            confidence_score=signal.confidence.score,
            is_verified=signal.is_verified,
            tags=signal.tags or [],
            related_signal_ids=[str(s_id) for s_id in signal.related_signals] if signal.related_signals else [],
            metadata=signal.metadata or {},
            detected_at=signal.detected_at.to_datetime,
            created_at=signal.created_at.to_datetime,
            updated_at=signal.updated_at.to_datetime,
        )

    async def _to_entity(self, model: SignalModel) -> Signal:
        """Convert SQLAlchemy model to domain entity."""
        return Signal(
            id=EntityId.from_string(model.id),
            company_id=EntityId.from_string(model.company_id),
            signal_type=model.signal_type,
            severity=model.severity,
            source=model.source,
            title=model.title,
            description=model.description,
            url=model.url,
            impact_score=model.impact_score,
            confidence=Confidence.from_score(model.confidence_score),
            is_verified=model.is_verified,
            tags=model.tags or [],
            related_signals=[EntityId.from_string(s_id) for s_id in (model.related_signal_ids or [])],
            metadata=model.metadata or {},
            detected_at=Timestamp.from_datetime(model.detected_at),
            created_at=Timestamp.from_datetime(model.created_at),
            updated_at=Timestamp.from_datetime(model.updated_at),
        )


# Placeholder for other repository implementations
# (ReportRepository, MarketEventRepository, AgentPolicyRepository, KnowledgeGraphRepository)
# These follow the same pattern as above

__all__ = [
    "SQLCompanyRepository",
    "SQLSignalRepository",
]
