"""
Vector Memory

Implements semantic retrieval using vector embeddings. Stores embeddings
for documents, reports, and research findings. Used for semantic search
and RAG (Retrieval-Augmented Generation).
"""

from .vector_memory import VectorMemory
from .embeddings import EmbeddingModel, SentenceTransformerEmbeddings

__all__ = [
    "VectorMemory",
    "EmbeddingModel",
    "SentenceTransformerEmbeddings",
]