"""
Database infrastructure module providing SQLAlchemy ORM models and async repository implementations.

This module bridges the domain layer with persistent storage, implementing all repository
interfaces defined in core.domain.interfaces.repositories using SQLAlchemy as the ORM.

Exports:
    - Database models (Company, Signal, Report, MarketEvent, AgentPolicy, KnowledgeNode, KnowledgeEdge)
    - SQLAlchemy engine and session factory
    - Async repository implementations
    - Migration utilities
"""

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./competitive_intelligence.db"  # Development
# For production, use: postgresql+asyncpg://user:password@localhost/dbname

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections every hour
)

# Create session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base for all models
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager to get database session.
    
    Usage:
        async with get_session() as session:
            # Use session
            pass
    """
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all database tables (use with caution!)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


__all__ = [
    "engine",
    "async_session_factory",
    "AsyncSession",
    "Base",
    "get_session",
    "init_db",
    "drop_db",
    "DATABASE_URL",
]
