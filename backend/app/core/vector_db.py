"""
Vector database abstraction layer.
Supports both Pinecone (recommended) and ChromaDB (for local development).
"""
from app.core.config import settings
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Import the appropriate vector DB based on configuration
if settings.VECTOR_DB_TYPE.lower() == "pinecone":
    from app.core.vector_db_pinecone import PineconeVectorDB
    _vector_db_impl = PineconeVectorDB()
    logger.info("Using Pinecone as vector database")
else:
    # ChromaDB implementation
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
    import uuid
    
    class ChromaVectorDB:
        """ChromaDB client wrapper."""
        
        def __init__(self):
            self._client = None
            self.collection = None
            self._initialized = False
            self._embedding_function = None
        
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
            if self._embedding_function is None:
                try:
                    self._embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=settings.OPENAI_API_KEY,
                        model_name=settings.OPENAI_EMBEDDING_MODEL
                    )
                except Exception as e:
                    logger.warning(f"Could not initialize OpenAI embedding function: {e}. Using default.")
                    self._embedding_function = None
            
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self._embedding_function,
                metadata={"description": "Persona generation documents"}
            )
            
            return self.collection
        
        async def add_documents(
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
        
        async def query_documents(
            self,
            query_texts: List[str],
            n_results: int = 5,
            collection_name: str = "persona_documents",
            filter_metadata: Optional[dict] = None
        ):
            """Query similar documents from the vector database."""
            collection = self.get_or_create_collection(collection_name)
            
            # Convert filter format for ChromaDB
            where = None
            if filter_metadata:
                # ChromaDB uses simple dict format or $in operator
                where = {}
                for key, value in filter_metadata.items():
                    if isinstance(value, dict) and "$in" in value:
                        # Handle $in operator for ChromaDB
                        where[key] = {"$in": value["$in"]}
                    else:
                        where[key] = value
            
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )
            
            return results
        
        async def update_document_metadata(
            self,
            vector_ids: List[str],
            metadata_updates: Dict[str, Any],
            collection_name: str = "persona_documents"
        ) -> bool:
            """
            Update metadata for existing vectors in ChromaDB.
            
            Note: ChromaDB doesn't have a direct update method, so we need to
            fetch, update, and re-add the vectors.
            """
            try:
                collection = self.get_or_create_collection(collection_name)
                
                # Fetch existing vectors
                existing = collection.get(ids=vector_ids, include=["metadatas", "embeddings"])
                
                if not existing or not existing.get("ids"):
                    logger.warning(f"No vectors found with IDs: {vector_ids}")
                    return False
                
                # Update metadata for each vector
                updated_metadatas = []
                for i, vector_id in enumerate(existing["ids"]):
                    existing_metadata = existing["metadatas"][i] if existing.get("metadatas") else {}
                    updated_metadata = {**existing_metadata, **metadata_updates}
                    updated_metadatas.append(updated_metadata)
                
                # Update vectors (ChromaDB update is done via upsert with same IDs)
                collection.update(
                    ids=existing["ids"],
                    metadatas=updated_metadatas
                )
                
                logger.info(f"Updated metadata for {len(existing['ids'])} vectors in ChromaDB")
                return True
            except Exception as e:
                logger.error(f"Error updating vector metadata in ChromaDB: {e}")
                return False
        
        def delete_collection(self, collection_name: str):
            """Delete a collection."""
            try:
                self.client.delete_collection(name=collection_name)
                return True
            except Exception:
                return False
    
    _vector_db_impl = ChromaVectorDB()
    logger.info("Using ChromaDB as vector database")


# Global vector DB instance (Pinecone or ChromaDB based on config)
vector_db = _vector_db_impl

