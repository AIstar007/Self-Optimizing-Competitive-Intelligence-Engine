"""Testing configuration and fixtures for pytest."""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

# ============================================================================
# Async Fixture Setup
# ============================================================================


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Create an async test client."""
    from fastapi.testclient import TestClient
    from core.interfaces.api import app
    
    with TestClient(app) as client:
        yield client


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    mock = AsyncMock()
    mock.generate_text = AsyncMock(return_value="Mock response")
    mock.generate_embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return mock


@pytest.fixture
def mock_browser_provider():
    """Mock browser provider."""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=[
        {"title": "Result 1", "url": "http://example1.com", "snippet": "Snippet 1"},
        {"title": "Result 2", "url": "http://example2.com", "snippet": "Snippet 2"},
    ])
    mock.get_page = AsyncMock(return_value="<html>Page content</html>")
    return mock


@pytest.fixture
def mock_repository():
    """Mock repository."""
    mock = AsyncMock()
    mock.create = AsyncMock(return_value={"id": "123", "created_at": "2026-03-15"})
    mock.get = AsyncMock(return_value={"id": "123", "data": "test"})
    mock.update = AsyncMock(return_value={"id": "123", "updated": True})
    mock.delete = AsyncMock(return_value=True)
    mock.list = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    mock = AsyncMock()
    mock.add_vector = AsyncMock(return_value="vec_id_123")
    mock.search = AsyncMock(return_value=[
        {"id": "1", "score": 0.9, "data": "Similar item 1"},
        {"id": "2", "score": 0.8, "data": "Similar item 2"},
    ])
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_knowledge_graph():
    """Mock knowledge graph."""
    mock = AsyncMock()
    mock.add_node = AsyncMock(return_value="node_id")
    mock.add_edge = AsyncMock(return_value="edge_id")
    mock.find_paths = AsyncMock(return_value=[["node1", "node2", "node3"]])
    mock.get_neighbors = AsyncMock(return_value=["neighbor1", "neighbor2"])
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_signal_data():
    """Sample signal data for testing."""
    return {
        "id": "signal_123",
        "title": "New partnership announced",
        "source": "techcrunch.com",
        "severity": "HIGH",
        "signal_type": "PARTNERSHIP",
        "verified": True,
        "content": "Company X announced partnership with Company Y",
    }


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "id": "comp_123",
        "name": "Acme Corp",
        "domain": "acme.com",
        "status": "ACTIVE",
        "stage": "GROWTH",
        "employees": 500,
        "markets": ["SaaS", "AI/ML"],
        "competitors": ["TechCorp", "InnovateLabs"],
    }


@pytest.fixture
def sample_report_data():
    """Sample report data for testing."""
    return {
        "id": "report_123",
        "report_type": "COMPETITIVE_ANALYSIS",
        "company_id": "comp_123",
        "content": "# Competitive Analysis\n\nThis is a comprehensive analysis...",
        "sections": {
            "executive_summary": "Summary content",
            "signals": "Signal analysis",
            "recommendations": "Key recommendations",
        },
        "word_count": 2500,
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "id": "wf_123",
        "company_id": "comp_123",
        "workflow_type": "competitive_intelligence",
        "status": "RUNNING",
        "tasks": [
            {"task_id": "task_1", "status": "COMPLETED"},
            {"task_id": "task_2", "status": "RUNNING"},
        ],
    }


# ============================================================================
# Context Manager Fixtures
# ============================================================================


@pytest.fixture
async def test_db_session():
    """Create a test database session."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.close()
    
    await engine.dispose()


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "llm_provider": "openai",
        "llm_model": "gpt-4",
        "browser": "chromium",
        "database": "sqlite:///:memory:",
        "debug": True,
    }


# ============================================================================
# Markers for Test Organization
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "async_test: mark test as async")
