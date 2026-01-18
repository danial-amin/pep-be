"""
Cohere reranking service for improving document retrieval relevance.

This service implements the reranking step from the PEP paper methodology,
using Cohere's rerank API to improve the relevance of retrieved document chunks.
"""
import cohere
from typing import List, Optional, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class CohereRerankService:
    """Cohere reranking service for document retrieval improvement."""

    def __init__(self):
        self._client = None
        self._initialized = False

    def _get_client(self) -> cohere.Client:
        """Lazy initialization of Cohere client."""
        if self._client is None:
            if not settings.COHERE_API_KEY:
                raise ValueError(
                    "COHERE_API_KEY is required for reranking. "
                    "Set it in your .env file or disable reranking with USE_COHERE_RERANKING=false"
                )

            try:
                self._client = cohere.Client(api_key=settings.COHERE_API_KEY)
                self._initialized = True
                logger.info("Cohere rerank client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Cohere client: {e}")
                raise

        return self._client

    @property
    def client(self) -> cohere.Client:
        """Get Cohere client (lazy initialization)."""
        return self._get_client()

    @property
    def is_available(self) -> bool:
        """Check if Cohere reranking is available and enabled."""
        return (
            settings.USE_COHERE_RERANKING
            and settings.COHERE_API_KEY is not None
            and len(settings.COHERE_API_KEY) > 0
        )

    async def rerank_documents(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
        return_documents: bool = True,
        max_chunks_to_rerank: int = 100
    ) -> Dict[str, Any]:
        """
        Rerank documents based on relevance to the query.

        This implements the search and ranking step from the PEP paper,
        using Cohere's semantic reranking to prioritize the most relevant
        document chunks for persona generation.

        Args:
            query: The search query (e.g., "user interviews, user research")
            documents: List of document texts to rerank
            top_n: Number of top results to return (default: all)
            return_documents: Whether to include document text in results
            max_chunks_to_rerank: Maximum number of chunks to send for reranking

        Returns:
            Dictionary with:
                - reranked_documents: List of documents in order of relevance
                - reranked_indices: Original indices of documents in relevance order
                - relevance_scores: Cohere relevance scores (0-1)
        """
        if not documents:
            return {
                "reranked_documents": [],
                "reranked_indices": [],
                "relevance_scores": []
            }

        # Limit documents to prevent API limits
        docs_to_rerank = documents[:max_chunks_to_rerank]

        if not self.is_available:
            logger.warning("Cohere reranking not available, returning documents in original order")
            return {
                "reranked_documents": docs_to_rerank,
                "reranked_indices": list(range(len(docs_to_rerank))),
                "relevance_scores": [1.0] * len(docs_to_rerank)
            }

        try:
            # Call Cohere rerank API
            response = self.client.rerank(
                model=settings.COHERE_RERANK_MODEL,
                query=query,
                documents=docs_to_rerank,
                top_n=top_n or len(docs_to_rerank),
                return_documents=return_documents
            )

            # Extract results
            reranked_documents = []
            reranked_indices = []
            relevance_scores = []

            for result in response.results:
                reranked_indices.append(result.index)
                relevance_scores.append(result.relevance_score)
                if return_documents and hasattr(result, 'document') and result.document:
                    reranked_documents.append(result.document.text)
                else:
                    reranked_documents.append(docs_to_rerank[result.index])

            logger.info(
                f"Reranked {len(docs_to_rerank)} documents. "
                f"Top relevance score: {relevance_scores[0] if relevance_scores else 'N/A'}"
            )

            return {
                "reranked_documents": reranked_documents,
                "reranked_indices": reranked_indices,
                "relevance_scores": relevance_scores
            }

        except Exception as e:
            logger.error(f"Cohere reranking failed: {e}. Falling back to original order.")
            return {
                "reranked_documents": docs_to_rerank,
                "reranked_indices": list(range(len(docs_to_rerank))),
                "relevance_scores": [1.0] * len(docs_to_rerank),
                "error": str(e)
            }

    async def rerank_with_metadata(
        self,
        query: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        top_n: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Rerank documents and return with associated metadata.

        Args:
            query: The search query
            documents: List of document texts
            metadatas: List of metadata dicts corresponding to documents
            top_n: Number of top results to return

        Returns:
            Dictionary with reranked documents, metadata, indices, and scores
        """
        result = await self.rerank_documents(
            query=query,
            documents=documents,
            top_n=top_n,
            return_documents=True
        )

        # Reorder metadata to match reranked order
        reranked_metadatas = [
            metadatas[idx] if idx < len(metadatas) else {}
            for idx in result["reranked_indices"]
        ]

        return {
            **result,
            "reranked_metadatas": reranked_metadatas
        }


# Global rerank service instance
rerank_service = CohereRerankService()
