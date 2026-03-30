"""
Domain Vector Store Interface

Defines the contract for vector storage and semantic search.
The infrastructure layer implements this interface.

Following Dependency Inversion Principle - the domain layer
defines what it needs from vector storage without coupling
to specific implementations (FAISS, Chroma, Pinecone, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Set, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class VectorDistance(Enum):
    """Distance metrics for vector similarity."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


@dataclass(frozen=True)
class Document:
    """
    A document stored in the vector store.

    Attributes:
        id: Unique document identifier
        content: The document text content
        embedding: The vector embedding (optional, can be computed)
        metadata: Associated metadata
        collection: Collection name
    """
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    collection: str = "default"

    @classmethod
    def create(
        cls,
        id: str,
        content: str,
        collection: str = "default",
        **metadata,
    ) -> "Document":
        """Create a document."""
        return cls(id, content, None, metadata, collection)


@dataclass(frozen=True)
class SearchResult:
    """
    A result from vector similarity search.

    Attributes:
        document: The matching document
        score: Similarity score (higher = more similar)
        distance: Distance metric value
    """
    document: Document
    score: float
    distance: float


@dataclass(frozen=True)
class VectorStats:
    """
    Statistics about a collection in the vector store.

    Attributes:
        collection: Collection name
        document_count: Number of documents
        dimension_count: Vector dimensions
        index_status: Status of the index
        last_updated: Last update timestamp
    """
    collection: str
    document_count: int
    dimension_count: int
    index_status: str
    last_updated: datetime


# ============================================================================
# Vector Store Interface
# ============================================================================


class VectorStore(ABC):
    """
    Interface for vector storage and semantic search.

    Provides methods for:
    - Storing documents with embeddings
    - Semantic similarity search
    - Managing collections
    """

    @abstractmethod
    async def add(
        self,
        document: Document,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        Add a document to the vector store.

        Args:
            document: The document to add
            embedding: Optional pre-computed embedding
        """
        pass

    @abstractmethod
    async def add_batch(
        self,
        documents: List[Document],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        Add multiple documents to the vector store.

        Args:
            documents: List of documents to add
            embeddings: Optional pre-computed embeddings
        """
        pass

    @abstractmethod
    async def upsert(
        self,
        document: Document,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        Add or update a document.

        Args:
            document: The document to add or update
            embedding: Optional pre-computed embedding
        """
        pass

    @abstractmethod
    async def upsert_batch(
        self,
        documents: List[Document],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        Add or update multiple documents.

        Args:
            documents: List of documents to add or update
            embeddings: Optional pre-computed embeddings
        """
        pass

    @abstractmethod
    async def get(
        self,
        document_id: str,
        collection: str = "default",
    ) -> Optional[Document]:
        """
        Get a document by ID.

        Args:
            document_id: The document ID
            collection: Collection name

        Returns:
            The document if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_batch(
        self,
        document_ids: List[str],
        collection: str = "default",
    ) -> List[Optional[Document]]:
        """
        Get multiple documents by IDs.

        Args:
            document_ids: List of document IDs
            collection: Collection name

        Returns:
            List of documents (None for not found)
        """
        pass

    @abstractmethod
    async def delete(
        self,
        document_id: str,
        collection: str = "default",
    ) -> bool:
        """
        Delete a document.

        Args:
            document_id: The document ID
            collection: Collection name

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_batch(
        self,
        document_ids: List[str],
        collection: str = "default",
    ) -> int:
        """
        Delete multiple documents.

        Args:
            document_ids: List of document IDs
            collection: Collection name

        Returns:
            Number of documents deleted
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        collection: str = "default",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search for similar documents by embedding.

        Args:
            query_embedding: The query vector
            collection: Collection to search
            limit: Maximum results to return
            filters: Optional metadata filters
            min_score: Minimum similarity score

        Returns:
            List of search results sorted by relevance
        """
        pass

    @abstractmethod
    async def search_by_text(
        self,
        query_text: str,
        collection: str = "default",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search for similar documents by text.

        The text will be embedded first.

        Args:
            query_text: The query text
            collection: Collection to search
            limit: Maximum results to return
            filters: Optional metadata filters
            min_score: Minimum similarity score

        Returns:
            List of search results sorted by relevance
        """
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        query_text: str,
        collection: str = "default",
        limit: int = 10,
        text_weight: float = 0.5,
        vector_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Hybrid search combining text and vector search.

        Args:
            query_text: The query text
            collection: Collection to search
            limit: Maximum results to return
            text_weight: Weight for text search (0-1)
            vector_weight: Weight for vector search (0-1)
            filters: Optional metadata filters

        Returns:
            List of search results sorted by combined relevance
        """
        pass

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        dimension: int,
        distance_metric: VectorDistance = VectorDistance.COSINE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a new collection.

        Args:
            name: Collection name
            dimension: Vector dimensions
            distance_metric: Distance metric
            metadata: Optional collection metadata
        """
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        """
        Delete a collection.

        Args:
            name: Collection name

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all collection names."""
        pass

    @abstractmethod
    async def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        pass

    @abstractmethod
    async def get_stats(self, collection: str = "default") -> Optional[VectorStats]:
        """
        Get statistics for a collection.

        Args:
            collection: Collection name

        Returns:
            Statistics if collection exists, None otherwise
        """
        pass

    @abstractmethod
    async def count(self, collection: str = "default") -> int:
        """
        Count documents in a collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents
        """
        pass

    @abstractmethod
    async def clear_collection(self, collection: str = "default") -> int:
        """
        Clear all documents from a collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents cleared
        """
        pass

    @abstractmethod
    async def list_documents(
        self,
        collection: str = "default",
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        List documents in a collection.

        Args:
            collection: Collection name
            limit: Maximum results
            offset: Pagination offset
            filters: Optional metadata filters

        Returns:
            List of documents
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get the default vector dimension."""
        pass

    @property
    @abstractmethod
    def default_collection(self) -> str:
        """Get the default collection name."""
        pass


# ============================================================================
# Export all interfaces
# ============================================================================


__all__ = [
    "VectorStore",
    "VectorDistance",
    "Document",
    "SearchResult",
    "VectorStats",
]