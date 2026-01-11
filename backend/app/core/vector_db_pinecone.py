"""
Pinecone vector database client.
"""
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings
from app.core.llm_service import llm_service
from typing import List, Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class PineconeVectorDB:
    """Pinecone vector database client wrapper."""
    
    def __init__(self):
        self._client = None
        self._index = None
        self._initialized = False
    
    def _get_client(self):
        """Lazy initialization of Pinecone client."""
        if self._client is None:
            if not settings.PINECONE_API_KEY:
                raise ValueError("PINECONE_API_KEY is required when using Pinecone")
            
            try:
                self._client = Pinecone(api_key=settings.PINECONE_API_KEY)
                self._initialized = True
                logger.info("Pinecone client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone client: {e}")
                raise
        return self._client
    
    @property
    def client(self):
        """Get Pinecone client (lazy initialization)."""
        return self._get_client()
    
    def _get_index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            index_name = settings.PINECONE_INDEX_NAME
            
            # Standardize on 1536 dimensions for all embeddings
            # This ensures consistency regardless of which embedding model is configured
            expected_dimension = 1536
            embedding_model = settings.OPENAI_EMBEDDING_MODEL
            
            # Log if model would produce different dimensions
            if "3-large" in embedding_model.lower():
                logger.info(
                    f"Embedding model '{embedding_model}' would produce 3072 dimensions, "
                    f"but standardizing to 1536 for consistency. "
                    f"LLM service will use text-embedding-3-small instead."
                )
            else:
                logger.info(f"Using standard dimension {expected_dimension} for embedding model {embedding_model}")
            
            # List existing indexes
            existing_indexes = [idx.name for idx in self.client.list_indexes()]
            
            if index_name not in existing_indexes:
                # Create index if it doesn't exist
                logger.info(f"Creating Pinecone index: {index_name} with dimension {expected_dimension}")
                
                # Determine spec based on environment
                # Free tier uses serverless
                # PINECONE_ENVIRONMENT format: "us-east-1-aws" or "us-west1-gcp" or "gcp-starter"
                if settings.PINECONE_ENVIRONMENT:
                    # Parse environment to get cloud and region
                    if "gcp" in settings.PINECONE_ENVIRONMENT.lower():
                        if "starter" in settings.PINECONE_ENVIRONMENT.lower():
                            # Free tier GCP starter
                            spec = ServerlessSpec(cloud="gcp", region="us-central1")
                        else:
                            # Extract region from format like "us-west1-gcp"
                            region = settings.PINECONE_ENVIRONMENT.split("-")[0] + "-" + settings.PINECONE_ENVIRONMENT.split("-")[1]
                            spec = ServerlessSpec(cloud="gcp", region=region)
                    elif "aws" in settings.PINECONE_ENVIRONMENT.lower():
                        # Extract region from format like "us-east-1-aws"
                        region = "-".join(settings.PINECONE_ENVIRONMENT.split("-")[:-1])
                        spec = ServerlessSpec(cloud="aws", region=region)
                    else:
                        # Default to AWS us-east-1
                        spec = ServerlessSpec(cloud="aws", region="us-east-1")
                else:
                    # Default to serverless AWS (free tier compatible)
                    spec = ServerlessSpec(cloud="aws", region="us-east-1")
                
                self.client.create_index(
                    name=index_name,
                    dimension=expected_dimension,
                    metric="cosine",
                    spec=spec
                )
                logger.info(f"Index {index_name} created successfully with dimension {expected_dimension}")
            else:
                # Check existing index dimension
                index_info = self.client.describe_index(index_name)
                existing_dimension = index_info.dimension
                
                if existing_dimension != expected_dimension:
                    error_msg = (
                        f"Pinecone index dimension mismatch!\n"
                        f"  Index '{index_name}' has dimension: {existing_dimension}\n"
                        f"  Embedding model '{embedding_model}' produces: {expected_dimension} dimensions\n\n"
                        f"Solutions:\n"
                        f"  1. Delete the existing index (will lose all vectors):\n"
                        f"     - Go to Pinecone dashboard and delete index '{index_name}', OR\n"
                        f"     - Set environment variable AUTO_RECREATE_INDEX=true to auto-delete\n"
                        f"  2. Change embedding model to match index:\n"
                        f"     - For 1024 dimensions: No OpenAI model matches (index may be from different service)\n"
                        f"     - For 1536 dimensions: Set OPENAI_EMBEDDING_MODEL='text-embedding-3-small' or 'text-embedding-ada-002'\n"
                        f"     - For 3072 dimensions: Keep 'text-embedding-3-large' (current) and recreate index"
                    )
                    logger.error(error_msg)
                    
                    # Check if auto-recreate is enabled
                    import os
                    auto_recreate = os.getenv("AUTO_RECREATE_INDEX", "false").lower() == "true"
                    
                    if auto_recreate:
                        logger.warning(f"Auto-recreating index '{index_name}' due to dimension mismatch...")
                        try:
                            self.client.delete_index(index_name)
                            logger.info(f"Deleted index '{index_name}'")
                            
                            # Recreate with correct dimension
                            if settings.PINECONE_ENVIRONMENT:
                                if "gcp" in settings.PINECONE_ENVIRONMENT.lower():
                                    if "starter" in settings.PINECONE_ENVIRONMENT.lower():
                                        spec = ServerlessSpec(cloud="gcp", region="us-central1")
                                    else:
                                        region = settings.PINECONE_ENVIRONMENT.split("-")[0] + "-" + settings.PINECONE_ENVIRONMENT.split("-")[1]
                                        spec = ServerlessSpec(cloud="gcp", region=region)
                                elif "aws" in settings.PINECONE_ENVIRONMENT.lower():
                                    region = "-".join(settings.PINECONE_ENVIRONMENT.split("-")[:-1])
                                    spec = ServerlessSpec(cloud="aws", region=region)
                                else:
                                    spec = ServerlessSpec(cloud="aws", region="us-east-1")
                            else:
                                spec = ServerlessSpec(cloud="aws", region="us-east-1")
                            
                            self.client.create_index(
                                name=index_name,
                                dimension=expected_dimension,
                                metric="cosine",
                                spec=spec
                            )
                            logger.info(f"Recreated index '{index_name}' with dimension {expected_dimension}")
                        except Exception as e:
                            logger.error(f"Failed to auto-recreate index: {e}")
                            raise ValueError(error_msg)
                    else:
                        raise ValueError(error_msg)
                else:
                    logger.info(f"Index {index_name} exists with matching dimension {existing_dimension}")
            
            # Connect to index
            self._index = self.client.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
        
        return self._index
    
    @property
    def index(self):
        """Get Pinecone index (lazy initialization)."""
        return self._get_index()
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "persona_documents"
    ) -> List[str]:
        """
        Add documents to Pinecone.
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dicts
            ids: Optional list of IDs (generated if not provided)
            collection_name: Not used for Pinecone (kept for API compatibility)
        
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Generate embeddings (async)
        logger.info(f"Creating embeddings for {len(documents)} documents")
        embeddings = await llm_service.create_embeddings(documents)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Prepare metadata (Pinecone requires text to be in metadata if you want to retrieve it)
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        # Add text to metadata for retrieval
        vectors_to_upsert = []
        for i, (embedding, doc_text, metadata, doc_id) in enumerate(zip(embeddings, documents, metadatas, ids)):
            # Pinecone metadata can store text (up to 40KB per vector)
            # Store text in metadata for retrieval
            metadata_with_text = {
                **metadata,
                "text": doc_text[:40000]  # Limit to 40KB
            }
            
            vectors_to_upsert.append({
                "id": doc_id,
                "values": embedding,
                "metadata": metadata_with_text
            })
        
        # Upsert in batches (Pinecone recommends batches of 100)
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")
        
        return ids
    
    async def query_documents(
        self,
        query_texts: List[str],
        n_results: int = 5,
        collection_name: str = "persona_documents",
        filter_metadata: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Query similar documents from Pinecone.
        
        Args:
            query_texts: List of query texts
            n_results: Number of results to return
            collection_name: Not used (kept for API compatibility)
            filter_metadata: Metadata filter (Pinecone filter format)
        
        Returns:
            Dictionary with 'documents' and 'metadatas' keys
        """
        if not query_texts:
            return {"documents": [], "metadatas": []}
        
        # Generate query embedding (async)
        query_embedding = await llm_service.create_query_embedding(query_texts[0])
        
        # Build filter if provided
        filter_dict = None
        if filter_metadata:
            # Convert simple filter to Pinecone format
            filter_dict = {}
            for key, value in filter_metadata.items():
                if isinstance(value, dict):
                    # Already in Pinecone format (e.g., {"$in": [...]})
                    filter_dict[key] = value
                else:
                    # Simple equality filter
                    filter_dict[key] = {"$eq": value}
        
        # Query Pinecone
        query_response = self.index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True,
            filter=filter_dict
        )
        
        # Format response to match ChromaDB format
        documents = []
        metadatas = []
        distances = []
        ids = []
        
        for match in query_response.matches:
            # Extract text from metadata
            text = match.metadata.get("text", "")
            documents.append(text)
            
            # Remove text from metadata for response (keep original metadata)
            metadata = {k: v for k, v in match.metadata.items() if k != "text"}
            metadatas.append(metadata)
            
            distances.append(match.score)
            ids.append(match.id)
        
        return {
            "documents": [documents],  # ChromaDB format: list of lists
            "metadatas": [metadatas],
            "distances": [distances],
            "ids": [ids]
        }
    
    async def update_document_metadata(
        self,
        vector_ids: List[str],
        metadata_updates: Dict[str, Any],
        collection_name: str = "persona_documents"
    ) -> bool:
        """
        Update metadata for existing vectors.
        
        Args:
            vector_ids: List of vector IDs to update
            metadata_updates: Dictionary of metadata fields to update
            collection_name: Not used (kept for API compatibility)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch existing vectors
            fetch_response = self.index.fetch(ids=vector_ids)
            
            # Update metadata for each vector
            vectors_to_upsert = []
            for vector_id in vector_ids:
                if vector_id in fetch_response.vectors:
                    vector_data = fetch_response.vectors[vector_id]
                    # Merge existing metadata with updates
                    updated_metadata = {
                        **vector_data.metadata,
                        **metadata_updates
                    }
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": vector_data.values,
                        "metadata": updated_metadata
                    })
            
            if vectors_to_upsert:
                self.index.upsert(vectors=vectors_to_upsert)
                logger.info(f"Updated metadata for {len(vectors_to_upsert)} vectors")
            
            return True
        except Exception as e:
            logger.error(f"Error updating vector metadata: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete Pinecone index (collection)."""
        try:
            self.client.delete_index(settings.PINECONE_INDEX_NAME)
            self._index = None
            return True
        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            return False


# Global Pinecone instance
pinecone_vector_db = PineconeVectorDB()

