"""
Document processing service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from pathlib import Path
import aiofiles
import os
import logging

from app.models.document import Document, DocumentType, ProcessingStatus
from app.core.llm_service import llm_service
from app.core.vector_db import vector_db
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.utils.token_utils import chunk_text_by_tokens

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document processing."""
    
    @staticmethod
    async def process_document(
        session: AsyncSession,
        file_path: str,
        filename: str,
        document_type: DocumentType,
        content: str,
        project_id: Optional[int] = None
    ) -> Document:
        """
        Process a document for retrieval (RAG): store text + chunk + embed + upsert vectors.

        IMPORTANT: Ingestion should not call chat-completions per chunk; that is slow/expensive
        and will routinely exceed background job timeouts. If you want an LLM-generated summary,
        enable it explicitly via DOCUMENT_SUMMARIZE_ON_INGEST.
        """

        processed_content = content
        if (
            settings.DOCUMENT_SUMMARIZE_ON_INGEST
            and len(content) > 100
            and not filename.startswith("default_")
            and not filename.startswith("transcripts-")
        ):
            try:
                processed_data = await llm_service.process_document(content, document_type.value)
                processed_content = str(processed_data)
            except Exception as e:
                logger.warning(f"LLM summarization failed, using raw content: {e}")
                processed_content = content
        
        # Store document in database first to get the document ID
        # This allows us to include document_id in vector metadata for filtering
        document = Document(
            filename=filename,
            document_type=document_type,
            content=content,
            processed_content=processed_content,
            project_id=project_id,  # Store project_id for session isolation
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        session.add(document)
        await session.flush()
        await session.refresh(document)
        
        # Create embeddings and store in vector DB with document_id in metadata
        vector_ids = []
        vector_storage_error = None
        try:
            # Use token-aware chunking for better embeddings
            from app.utils.token_utils import chunk_text_by_tokens
            
            # Chunk by tokens (better for embeddings) - use smaller chunks for embeddings
            chunks = chunk_text_by_tokens(
                content,
                max_tokens=8000,  # Smaller chunks for embeddings (embedding models handle this well)
                overlap_tokens=200
            )
            
            if not chunks:
                raise ValueError("No chunks created from document content")
            
            # Prepare metadata with document_id and project_id for filtering and isolation
            metadata_base = {
                "document_type": document_type.value,
                "filename": filename,
                "document_id": str(document.id),  # Store document_id for filtering
            }
            if project_id:
                metadata_base["project_id"] = str(project_id)  # Store project_id for filtering
            
            metadatas = [
                {
                    **metadata_base,
                    "chunk_index": i,
                    "text_content": chunks[i]  # Store chunk content for Pinecone
                }
                for i in range(len(chunks))
            ]
            
            # Store in vector DB (Pinecone or ChromaDB will create embeddings)
            logger.info(f"Storing {len(chunks)} chunks in vector DB for document {document.id}")
            vector_ids = await vector_db.add_documents(
                documents=chunks,
                metadatas=metadatas
            )
            
            if not vector_ids:
                raise ValueError("No vector IDs returned from vector DB storage")
            
            # Update document with first vector_id as reference
            document.vector_id = vector_ids[0] if vector_ids else None
            await session.flush()
            logger.info(f"Successfully stored {len(vector_ids)} chunks in vector DB for document {document.id}")
        except Exception as e:
            vector_storage_error = str(e)
            logger.error(f"Vector DB storage failed for {filename}: {e}", exc_info=True)
            # Store error in document for visibility
            document.vector_id = None
            await session.flush()
            # Re-raise the error so the API can return appropriate response
            raise ValueError(f"Document saved to database but vector storage failed: {vector_storage_error}")
        
        return document

    @staticmethod
    async def create_pending_document(
        session: AsyncSession,
        file_path: str,
        filename: str,
        document_type: DocumentType,
        project_id: Optional[int] = None,
    ) -> Document:
        """Create a document record with status pending. Processing runs in background."""
        document = Document(
            filename=filename,
            document_type=document_type,
            content=None,
            processed_content=None,
            project_id=project_id,
            file_path=file_path,
            processing_status=ProcessingStatus.PENDING,
        )
        session.add(document)
        await session.flush()
        await session.refresh(document)
        return document

    @staticmethod
    async def process_document_content_into_existing(
        session: AsyncSession,
        document: Document,
        content: str,
    ) -> None:
        """
        Update an existing document: store text + chunk + embed + upsert vectors.

        By default, does NOT run chat-completions summarization. See DOCUMENT_SUMMARIZE_ON_INGEST.
        """
        filename = document.filename
        document_type = document.document_type
        project_id = document.project_id

        processed_content = content
        if (
            settings.DOCUMENT_SUMMARIZE_ON_INGEST
            and len(content) > 100
            and not filename.startswith("default_")
            and not filename.startswith("transcripts-")
        ):
            try:
                processed_data = await llm_service.process_document(content, document_type.value)
                processed_content = str(processed_data)
            except Exception as e:
                logger.warning(f"LLM summarization failed, using raw content: {e}")
                processed_content = content

        document.content = content
        document.processed_content = processed_content
        await session.flush()

        from app.utils.token_utils import chunk_text_by_tokens

        chunks = chunk_text_by_tokens(content, max_tokens=8000, overlap_tokens=200)
        if not chunks:
            raise ValueError("No chunks created from document content")

        metadata_base = {
            "document_type": document_type.value,
            "filename": filename,
            "document_id": str(document.id),
        }
        if project_id:
            metadata_base["project_id"] = str(project_id)

        metadatas = [
            {**metadata_base, "chunk_index": i, "text_content": chunks[i]}
            for i in range(len(chunks))
        ]

        logger.info(f"Storing {len(chunks)} chunks in vector DB for document {document.id}")
        vector_ids = await vector_db.add_documents(documents=chunks, metadatas=metadatas)
        if not vector_ids:
            raise ValueError("No vector IDs returned from vector DB storage")

        document.vector_id = vector_ids[0]
        await session.flush()
        logger.info(f"Successfully stored {len(vector_ids)} chunks in vector DB for document {document.id}")

    @staticmethod
    async def process_document_background(document_id: int) -> None:
        """
        Background task: load document, extract text from file, run full processing, update document.
        Uses its own database session. Cleans up file on disk when done (success or failure).
        """
        from app.utils.file_processing import extract_text_from_file

        file_path_to_delete: Optional[str] = None
        content: Optional[str] = None

        async with AsyncSessionLocal() as session:
            try:
                document = await DocumentService.get_document(session, document_id)
                if not document or document.processing_status != ProcessingStatus.PENDING:
                    return
                if not document.file_path:
                    logger.error(f"Document {document_id} has no file_path")
                    document.processing_status = ProcessingStatus.FAILED
                    document.processing_error = "No file path for pending document"
                    await session.commit()
                    return

                document.processing_status = ProcessingStatus.PROCESSING
                await session.commit()
                file_path_to_delete = document.file_path

                fp = Path(document.file_path)
                if not fp.exists():
                    document.processing_status = ProcessingStatus.FAILED
                    document.processing_error = "Stored file not found"
                    await session.commit()
                    return

                file_ext = fp.suffix.lower()
                content = await extract_text_from_file(str(fp), file_ext)
                if not (content and content.strip()):
                    document.processing_status = ProcessingStatus.FAILED
                    document.processing_error = "No text extracted from file"
                    await session.commit()
                    content = None
                    return
            except Exception as e:
                logger.exception(f"Error loading document {document_id} for background processing: {e}")
                async with AsyncSessionLocal() as session2:
                    doc = await DocumentService.get_document(session2, document_id)
                    if doc:
                        doc.processing_status = ProcessingStatus.FAILED
                        doc.processing_error = str(e)
                        await session2.commit()
                        file_path_to_delete = doc.file_path
                if file_path_to_delete and Path(file_path_to_delete).exists():
                    try:
                        Path(file_path_to_delete).unlink()
                    except OSError:
                        pass
                return

        if not content:
            return

        try:
            async with AsyncSessionLocal() as session:
                document = await DocumentService.get_document(session, document_id)
                if not document or document.processing_status != ProcessingStatus.PROCESSING:
                    return
                await DocumentService.process_document_content_into_existing(session, document, content)
                document.processing_status = ProcessingStatus.COMPLETED
                document.processing_error = None
                document.file_path = None
                await session.commit()
        except Exception as e:
            logger.exception(f"Background processing failed for document {document_id}: {e}")
            async with AsyncSessionLocal() as session:
                doc = await DocumentService.get_document(session, document_id)
                if doc:
                    doc.processing_status = ProcessingStatus.FAILED
                    doc.processing_error = str(e)
                    doc.file_path = None
                    await session.commit()
        finally:
            if file_path_to_delete and Path(file_path_to_delete).exists():
                try:
                    Path(file_path_to_delete).unlink()
                    logger.info(f"Removed stored file {file_path_to_delete}")
                except OSError as err:
                    logger.warning(f"Could not remove file {file_path_to_delete}: {err}")
    
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
    async def retry_document_processing(
        session: AsyncSession,
        document_id: int,
    ) -> Optional[str]:
        """
        Retry processing for a document that has a file (e.g. stuck in pending/processing).
        Supports both local storage and S3 (Railway Buckets).
        Returns None on success, or an error message string on failure.
        """
        from app.utils.file_processing import extract_text_from_file
        from app.core.storage import S3_KEY_PREFIX, fetch_to_temp_file, delete_file

        document = await DocumentService.get_document(session, document_id)
        if not document:
            return "Document not found"
        if not document.file_path:
            return "No file path; cannot retry from file. Re-upload the document or use /reprocess if content exists."
        storage_location = document.file_path
        temp_path: Optional[str] = None
        try:
            if storage_location.startswith(S3_KEY_PREFIX):
                suffix = Path(document.filename).suffix if document.filename else ""
                temp_path = await fetch_to_temp_file(storage_location, suffix=suffix)
                file_path = temp_path
            else:
                fp = Path(storage_location)
                if not fp.exists():
                    document.processing_status = ProcessingStatus.FAILED
                    document.processing_error = "Stored file not found (retry)"
                    await session.flush()
                    return "Stored file not found. Re-upload the document."
                file_path = str(fp)
            file_ext = Path(document.filename).suffix.lower()
            content = await extract_text_from_file(file_path, file_ext)
        except Exception as e:
            document.processing_status = ProcessingStatus.FAILED
            document.processing_error = str(e)
            await session.flush()
            return f"Text extraction failed: {e}"
        finally:
            if temp_path and Path(temp_path).exists():
                try:
                    Path(temp_path).unlink()
                except OSError:
                    pass
        if not (content and content.strip()):
            document.processing_status = ProcessingStatus.FAILED
            document.processing_error = "No text extracted from file"
            await session.flush()
            return "No text extracted from file"
        document.processing_status = ProcessingStatus.PROCESSING
        await session.flush()
        try:
            await vector_db.delete_documents(filter_metadata={"document_id": str(document.id)})
            await DocumentService.process_document_content_into_existing(session, document, content)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processing_error = None
            document.file_path = None
            await session.flush()
            if storage_location:
                await delete_file(storage_location)
            return None
        except Exception as e:
            document.processing_status = ProcessingStatus.FAILED
            document.processing_error = str(e)
            await session.flush()
            return str(e)

    @staticmethod
    async def reprocess_documents(
        session: AsyncSession,
        document_ids: Optional[List[int]] = None,
        force: bool = False,
    ) -> dict:
        """
        Reprocess documents that have content but no/missing vectors (content → chunks → vector DB).
        Use for old documents that were processed but vectors were lost, or vector storage failed.
        Returns { "processed": [ids], "skipped": [ids], "errors": [{"document_id": id, "error": str}] }.
        """
        query = select(Document).where(
            Document.content.isnot(None),
            Document.content != "",
        )
        if document_ids is not None:
            query = query.where(Document.id.in_(document_ids))
        if not force:
            query = query.where(Document.vector_id.is_(None))
        result = await session.execute(query)
        candidates = list(result.scalars().all())

        processed: List[int] = []
        skipped: List[int] = []
        errors: List[dict] = []

        for doc in candidates:
            content = (doc.content or "").strip()
            if not content:
                skipped.append(doc.id)
                continue
            if doc.vector_id and not force:
                skipped.append(doc.id)
                continue

            try:
                if force and doc.vector_id:
                    await vector_db.delete_documents(
                        filter_metadata={"document_id": str(doc.id)}
                    )
                chunks = chunk_text_by_tokens(
                    content,
                    max_tokens=8000,
                    overlap_tokens=200,
                )
                if not chunks:
                    errors.append({"document_id": doc.id, "error": "No chunks created"})
                    continue
                metadata_base = {
                    "document_type": doc.document_type.value,
                    "filename": doc.filename,
                    "document_id": str(doc.id),
                }
                if doc.project_id is not None:
                    metadata_base["project_id"] = str(doc.project_id)
                metadatas = [
                    {**metadata_base, "chunk_index": i, "text_content": chunks[i]}
                    for i in range(len(chunks))
                ]
                vector_ids = await vector_db.add_documents(
                    documents=chunks,
                    metadatas=metadatas,
                )
                doc.vector_id = vector_ids[0] if vector_ids else None
                doc.processing_status = ProcessingStatus.COMPLETED
                doc.processing_error = None
                await session.flush()
                processed.append(doc.id)
                logger.info(
                    "Reprocessed document %s (%d chunks)",
                    doc.id,
                    len(vector_ids) if vector_ids else 0,
                )
            except Exception as e:
                logger.exception("Reprocess failed for document %s: %s", doc.id, e)
                errors.append({"document_id": doc.id, "error": str(e)})

        return {"processed": processed, "skipped": skipped, "errors": errors}

    @staticmethod
    async def get_need_reupload(
        session: AsyncSession,
        project_id: Optional[int] = None,
    ) -> List[Document]:
        """
        Return documents that are pending/failed and have no content (file was lost).
        User should re-upload these.
        """
        query = select(Document).where(
            Document.processing_status.in_(
                [ProcessingStatus.PENDING, ProcessingStatus.FAILED]
            ),
            or_(
                Document.content.is_(None),
                Document.content == "",
            ),
        )
        if project_id is not None:
            query = query.where(Document.project_id == project_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_document(
        session: AsyncSession,
        document_id: int
    ) -> bool:
        """Delete a document and its vectors. Also removes stored file if present (local or S3)."""
        from app.core.storage import delete_file

        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        storage_location = document.file_path
        await vector_db.delete_documents(filter_metadata={"document_id": str(document.id)})
        await session.delete(document)
        await session.flush()

        if storage_location:
            await delete_file(storage_location)
        return True
    
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

