"""
Document processing service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import aiofiles
import os

from app.models.document import Document, DocumentType
from app.core.llm_service import llm_service
from app.core.vector_db import vector_db
from app.core.config import settings


class DocumentService:
    """Service for document processing."""
    
    @staticmethod
    async def process_document(
        session: AsyncSession,
        file_path: str,
        filename: str,
        document_type: DocumentType,
        content: str
    ) -> Document:
        """Process a document: extract text, process with LLM, create embeddings."""
        
        # Process with LLM
        processed_data = await llm_service.process_document(content, document_type.value)
        processed_content = str(processed_data)
        
        # Create embeddings and store in vector DB
        # Use token-aware chunking for better embeddings
        from app.utils.token_utils import chunk_text_by_tokens
        
        # Chunk by tokens (better for embeddings) - use smaller chunks for embeddings
        # ChromaDB will automatically create embeddings using the configured embedding function
        chunks = chunk_text_by_tokens(
            content,
            max_tokens=8000,  # Smaller chunks for embeddings (embedding models handle this well)
            overlap_tokens=200
        )
        
        metadatas = [
            {
                "document_type": document_type.value,
                "filename": filename,
                "chunk_index": i
            }
            for i in range(len(chunks))
        ]
        
        # Store in vector DB (Pinecone or ChromaDB will create embeddings)
        vector_ids = await vector_db.add_documents(
            documents=chunks,
            metadatas=metadatas
        )
        
        # Store document in database
        document = Document(
            filename=filename,
            document_type=document_type,
            content=content,
            processed_content=processed_content,
            vector_id=vector_ids[0] if vector_ids else None  # Store first vector ID as reference
        )
        
        session.add(document)
        await session.flush()
        await session.refresh(document)
        
        # Update vector DB metadata with document ID for better tracking
        # Note: This would require updating ChromaDB metadata, which may need
        # the document IDs. For now, we store the first vector_id as reference.
        # In a production system, you might want to update metadata after document creation.
        
        return document
    
    @staticmethod
    async def get_documents_by_type(
        session: AsyncSession,
        document_type: DocumentType
    ) -> List[Document]:
        """Get all documents of a specific type."""
        result = await session.execute(
            select(Document).where(Document.document_type == document_type)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_document(
        session: AsyncSession,
        document_id: int
    ) -> Optional[Document]:
        """Get a document by ID."""
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into chunks with overlap."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks

