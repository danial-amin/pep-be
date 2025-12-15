"""
Vector database (ChromaDB) configuration and client.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from typing import List, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class VectorDB:
    """ChromaDB client wrapper."""
    
    def __init__(self):
        self._client = None
        self.collection = None
        self._initialized = False
    
    def _get_client(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise
        return self._client
    
    @property
    def client(self):
        """Get ChromaDB client (lazy initialization)."""
        return self._get_client()
    
    def get_or_create_collection(self, collection_name: str = "persona_documents"):
        """Get or create a collection for storing document embeddings."""
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Persona generation documents"}
        )
        return self.collection
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "persona_documents"
    ):
        """Add documents to the vector database."""
        collection = self.get_or_create_collection(collection_name)
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def query_documents(
        self,
        query_texts: List[str],
        n_results: int = 5,
        collection_name: str = "persona_documents",
        filter_metadata: Optional[dict] = None
    ):
        """Query similar documents from the vector database."""
        collection = self.get_or_create_collection(collection_name)
        
        where = filter_metadata if filter_metadata else None
        
        results = collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where
        )
        
        return results
    
    def delete_collection(self, collection_name: str):
        """Delete a collection."""
        try:
            self.client.delete_collection(name=collection_name)
            return True
        except Exception:
            return False


# Global vector DB instance
vector_db = VectorDB()

