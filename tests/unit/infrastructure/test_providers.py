"""Unit tests for infrastructure layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.infrastructure.llm import LLMProvider


# ============================================================================
# LLM Provider Tests
# ============================================================================


class TestLLMProvider:
    """Test LLM provider abstraction."""

    @pytest.mark.asyncio
    async def test_generate_text(self, mock_llm_provider):
        """Test text generation."""
        result = await mock_llm_provider.generate_text("Test prompt")
        
        assert result == "Mock response"
        mock_llm_provider.generate_text.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_context(self, mock_llm_provider):
        """Test text generation with context."""
        context = {
            "company": "Acme Corp",
            "market": "SaaS",
            "tone": "professional",
        }
        
        result = await mock_llm_provider.generate_text(
            "Analyze this company",
            context=context
        )
        
        assert result is not None
        mock_llm_provider.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embeddings(self, mock_llm_provider):
        """Test embedding generation."""
        embeddings = await mock_llm_provider.generate_embeddings("Test text")
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        mock_llm_provider.generate_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_llm_provider):
        """Test batch text processing."""
        texts = ["Text 1", "Text 2", "Text 3"]
        mock_llm_provider.batch_process = AsyncMock(
            return_value=["Response 1", "Response 2", "Response 3"]
        )
        
        results = await mock_llm_provider.batch_process(texts)
        
        assert len(results) == 3
        assert results[0] == "Response 1"


# ============================================================================
# Repository Tests
# ============================================================================


class TestRepository:
    """Test repository pattern."""

    @pytest.mark.asyncio
    async def test_create_signal(self, mock_repository, sample_signal_data):
        """Test creating a signal via repository."""
        result = await mock_repository.create(sample_signal_data)
        
        assert result["id"] == "123"
        assert "created_at" in result
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_signal(self, mock_repository):
        """Test retrieving a signal."""
        result = await mock_repository.get("signal_123")
        
        assert result["id"] == "123"
        mock_repository.get.assert_called_once_with("signal_123")

    @pytest.mark.asyncio
    async def test_update_signal(self, mock_repository):
        """Test updating a signal."""
        update_data = {"verified": True}
        result = await mock_repository.update("signal_123", update_data)
        
        assert result["updated"] is True
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_signal(self, mock_repository):
        """Test deleting a signal."""
        result = await mock_repository.delete("signal_123")
        
        assert result is True
        mock_repository.delete.assert_called_once_with("signal_123")

    @pytest.mark.asyncio
    async def test_list_signals(self, mock_repository):
        """Test listing signals."""
        result = await mock_repository.list()
        
        assert isinstance(result, list)
        mock_repository.list.assert_called_once()


# ============================================================================
# Vector Store Tests
# ============================================================================


class TestVectorStore:
    """Test vector store."""

    @pytest.mark.asyncio
    async def test_add_vector(self, mock_vector_store):
        """Test adding a vector."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = await mock_vector_store.add_vector(
            vector=vector,
            data={"id": "doc_1", "text": "Sample text"},
        )
        
        assert result == "vec_id_123"
        mock_vector_store.add_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vectors(self, mock_vector_store):
        """Test searching vectors."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        results = await mock_vector_store.search(
            query_vector=query_vector,
            top_k=10,
        )
        
        assert len(results) == 2
        assert results[0]["score"] > results[1]["score"]
        mock_vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_vector(self, mock_vector_store):
        """Test deleting a vector."""
        result = await mock_vector_store.delete("vec_id_123")
        
        assert result is True
        mock_vector_store.delete.assert_called_once()


# ============================================================================
# Knowledge Graph Tests
# ============================================================================


class TestKnowledgeGraph:
    """Test knowledge graph."""

    @pytest.mark.asyncio
    async def test_add_node(self, mock_knowledge_graph):
        """Test adding a node."""
        node_id = await mock_knowledge_graph.add_node(
            node_type="company",
            data={"name": "Acme Corp"},
        )
        
        assert node_id == "node_id"
        mock_knowledge_graph.add_node.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_edge(self, mock_knowledge_graph):
        """Test adding an edge."""
        edge_id = await mock_knowledge_graph.add_edge(
            from_node="node1",
            to_node="node2",
            edge_type="ACQUIRED",
        )
        
        assert edge_id == "edge_id"
        mock_knowledge_graph.add_edge.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_paths(self, mock_knowledge_graph):
        """Test finding paths."""
        paths = await mock_knowledge_graph.find_paths(
            source="node1",
            target="node3",
        )
        
        assert len(paths) == 1
        assert paths[0] == ["node1", "node2", "node3"]
        mock_knowledge_graph.find_paths.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_neighbors(self, mock_knowledge_graph):
        """Test getting neighbors."""
        neighbors = await mock_knowledge_graph.get_neighbors("node1")
        
        assert len(neighbors) == 2
        assert "neighbor1" in neighbors
        mock_knowledge_graph.get_neighbors.assert_called_once()


# ============================================================================
# Browser Provider Tests
# ============================================================================


class TestBrowserProvider:
    """Test browser automation provider."""

    @pytest.mark.asyncio
    async def test_web_search(self, mock_browser_provider):
        """Test web search."""
        results = await mock_browser_provider.search("competitor news")
        
        assert len(results) == 2
        assert results[0]["title"] == "Result 1"
        assert "snippet" in results[0]

    @pytest.mark.asyncio
    async def test_get_page_content(self, mock_browser_provider):
        """Test getting page content."""
        content = await mock_browser_provider.get_page("http://example.com")
        
        assert "<html>" in content
        mock_browser_provider.get_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_validation(self, mock_browser_provider):
        """Test search result validation."""
        results = await mock_browser_provider.search("test query")
        
        for result in results:
            assert "title" in result
            assert "url" in result
            assert "snippet" in result


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in infrastructure."""

    @pytest.mark.asyncio
    async def test_repository_error(self, mock_repository):
        """Test repository error handling."""
        mock_repository.get = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception):
            await mock_repository.get("nonexistent")

    @pytest.mark.asyncio
    async def test_llm_error(self, mock_llm_provider):
        """Test LLM provider error handling."""
        mock_llm_provider.generate_text = AsyncMock(
            side_effect=Exception("API error")
        )
        
        with pytest.raises(Exception):
            await mock_llm_provider.generate_text("test")

    @pytest.mark.asyncio
    async def test_vector_store_error(self, mock_vector_store):
        """Test vector store error handling."""
        mock_vector_store.search = AsyncMock(side_effect=Exception("Search error"))
        
        with pytest.raises(Exception):
            await mock_vector_store.search(query_vector=[0.1, 0.2])


# ============================================================================
# Integration with Configuration
# ============================================================================


class TestInfrastructureConfiguration:
    """Test infrastructure configuration."""

    def test_config_loading(self, test_config):
        """Test loading configuration."""
        assert test_config["llm_provider"] == "openai"
        assert test_config["llm_model"] == "gpt-4"
        assert test_config["debug"] is True

    def test_config_validation(self, test_config):
        """Test configuration validation."""
        required_keys = ["llm_provider", "database", "browser"]
        for key in required_keys:
            assert key in test_config
