# RAG (Retrieval Augmented Generation) Implementation

## Overview

The PEP system now uses a proper RAG architecture where documents are processed once, stored with embeddings, and retrieved semantically when needed.

## How It Works

### 1. Document Processing (One-Time)

When a document is uploaded:

1. **Text Extraction**: Document text is extracted (PDF, DOCX, TXT, MD)
2. **LLM Processing**: Document is analyzed by LLM to extract key information (with chunking for large docs)
3. **Chunking**: Document is split into semantic chunks (8,000 tokens each with 200 token overlap)
4. **Embedding Creation**: Each chunk is embedded using OpenAI's `text-embedding-3-large` model
5. **Vector Storage**: Chunks are stored in ChromaDB with metadata:
   - `document_type`: "context" or "interview"
   - `filename`: Original filename
   - `chunk_index`: Position in document
6. **Database Storage**: Document metadata stored in PostgreSQL

**Key Point**: Documents are processed ONCE and embeddings are created and stored permanently.

### 2. Persona Generation (RAG Retrieval)

When generating personas:

1. **Semantic Query**: System creates queries like:
   - "user interviews, user research, interview transcripts, user feedback"
   - "research context, background information, market research"
2. **Vector Search**: ChromaDB finds top 10 most relevant chunks for each query
3. **Filtered Retrieval**: Results filtered by document type (interview vs context)
4. **LLM Generation**: Only retrieved chunks are sent to LLM (not all documents)
5. **Persona Creation**: LLM generates personas based on relevant context

**Benefits**:
- ✅ Only relevant information is used (semantic search)
- ✅ Handles large document sets efficiently
- ✅ Avoids token limits
- ✅ Faster processing

### 3. Persona Expansion (Targeted RAG)

When expanding a persona:

1. **Persona-Based Query**: Query built from persona characteristics:
   - Name, occupation, description
   - "demographics psychographics behaviors goals challenges"
2. **Semantic Retrieval**: Top 8 most relevant context chunks retrieved
3. **Targeted Expansion**: LLM expands persona using only relevant context

### 4. Prompt Completion (Already Using RAG)

The prompt completion endpoint already uses RAG:
- Queries vector DB with user prompt
- Retrieves top 5 relevant chunks
- Uses retrieved context to complete prompt

## Interview Transcript Flow

For an interview transcript:

1. **Upload**: User uploads interview transcript as "interview" document type
2. **Processing**:
   - Transcript is chunked (preserving conversation flow where possible)
   - Each chunk is embedded
   - Chunks stored in vector DB with metadata: `document_type: "interview"`
3. **Storage**: 
   - Full transcript stored in PostgreSQL
   - Chunks with embeddings stored in ChromaDB
4. **Retrieval** (when generating personas):
   - System queries: "user interviews, interview transcripts, user feedback"
   - Vector DB returns most relevant interview chunks
   - Only these chunks are used for persona generation

## Architecture Benefits

### Before (Without RAG)
- ❌ Loaded ALL documents from database
- ❌ Sent entire documents to LLM
- ❌ Hit token limits with large document sets
- ❌ No semantic understanding of relevance

### After (With RAG)
- ✅ Only retrieves relevant chunks
- ✅ Semantic search finds most relevant information
- ✅ Handles unlimited document sets
- ✅ Faster and more efficient
- ✅ Better quality (only relevant context)

## Configuration

The system uses:
- **Embedding Model**: `text-embedding-3-large` (OpenAI)
- **Chunk Size**: 8,000 tokens for embeddings (smaller than processing chunks)
- **Overlap**: 200 tokens between chunks
- **Retrieval**: Top 10 chunks for persona generation, Top 8 for expansion

## Data Flow

```
Document Upload
    ↓
Text Extraction
    ↓
LLM Processing (chunked if large)
    ↓
Token-Aware Chunking (8k tokens)
    ↓
Embedding Creation (OpenAI)
    ↓
Storage in ChromaDB (with metadata)
    ↓
[Document Ready for RAG Retrieval]

Persona Generation Request
    ↓
Semantic Query Creation
    ↓
Vector Search (ChromaDB)
    ↓
Retrieve Top Relevant Chunks
    ↓
Send to LLM (only relevant chunks)
    ↓
Generate Personas
```

## Key Files

- `app/core/vector_db.py`: ChromaDB client with OpenAI embeddings
- `app/services/document_service.py`: Document processing and chunking
- `app/services/persona_service.py`: RAG-based persona generation
- `app/utils/token_utils.py`: Token-aware chunking utilities

## Future Improvements

1. **Hybrid Search**: Combine semantic search with keyword search
2. **Re-ranking**: Re-rank retrieved chunks for better relevance
3. **Metadata Filtering**: More sophisticated filtering (date ranges, sources, etc.)
4. **Chunk Optimization**: Better chunking strategies (sentence-aware, paragraph-aware)
5. **Embedding Caching**: Cache embeddings to avoid re-computation

