# Session Isolation for Vector Database

## Problem

When multiple users or sessions create personas using the same vector database index, documents from different persona creation sessions get mixed together. This causes:

1. **Cross-contamination**: Personas generated in one session might use documents from another session
2. **No isolation**: All documents are stored in the same vector index without separation
3. **Privacy concerns**: Documents from different projects/sessions are accessible to each other

## Solution

We've implemented session isolation using two approaches:

### 1. Project ID Filtering

Documents can be tagged with a `project_id` when uploaded:

```python
# When uploading a document
POST /api/v1/documents/process
{
    "file": ...,
    "document_type": "interview",
    "project_id": "project-123"  # Optional project identifier
}
```

### 2. Document ID Filtering

When generating personas, you can specify which documents to use:

```python
# When generating personas
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "document_ids": [1, 2, 3],  # Only use these specific documents
    # OR
    "project_id": "project-123"  # Use all documents from this project
}
```

## Implementation Details

### Database Changes

1. **Document Model**: Added `project_id` field (nullable, indexed)
   - Allows grouping documents by project/session
   - Indexed for fast filtering

2. **Vector Metadata**: Each document chunk stores `document_id` in metadata
   - Enables filtering vector queries by document ID
   - Supports both Pinecone and ChromaDB

### Vector Database Filtering

When querying the vector database for persona generation:

1. **Filter by document_ids**: Only retrieve chunks from specified documents
2. **Filter by project_id**: Retrieve chunks from all documents in a project
3. **Default behavior**: If no filter provided, uses all documents (backward compatible)

### API Changes

#### Document Upload Endpoint
```python
POST /api/v1/documents/process
- Added optional `project_id` parameter
```

#### Persona Generation Endpoint
```python
POST /api/v1/personas/generate-set
- Added optional `document_ids` parameter (list of document IDs)
- Added optional `project_id` parameter (alternative to document_ids)
```

## Usage Examples

### Example 1: Project-Based Isolation

```python
# Step 1: Upload documents with project_id
project_id = "user-research-2024"

# Upload interview documents
POST /api/v1/documents/process
{
    "file": interview1.pdf,
    "document_type": "interview",
    "project_id": project_id
}

POST /api/v1/documents/process
{
    "file": interview2.pdf,
    "document_type": "interview",
    "project_id": project_id
}

# Step 2: Generate personas using only documents from this project
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "project_id": project_id  # Only uses documents with this project_id
}
```

### Example 2: Document ID-Based Isolation

```python
# Step 1: Upload documents (get document IDs from responses)
doc1 = POST /api/v1/documents/process {...}  # Returns document with id=1
doc2 = POST /api/v1/documents/process {...}  # Returns document with id=2

# Step 2: Generate personas using specific documents
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "document_ids": [1, 2]  # Only uses these specific documents
}
```

## Migration

Run the migration to add the `project_id` column:

```bash
alembic upgrade head
```

This will:
- Add `project_id` column to `documents` table
- Create index on `project_id` for faster queries

## Backward Compatibility

- Existing documents without `project_id` will have `NULL` values
- If no `document_ids` or `project_id` is provided when generating personas, the system uses all documents (original behavior)
- This ensures existing code continues to work

## Best Practices

1. **Use project_id for multi-session scenarios**: When different users/projects need isolation
2. **Use document_ids for fine-grained control**: When you need to select specific documents
3. **Generate unique project_ids**: Use UUIDs or timestamps to ensure uniqueness
4. **Clean up old projects**: Consider deleting documents/projects when no longer needed

## Technical Notes

### Vector Database Support

- **Pinecone**: Supports `$in` operator for filtering by multiple document IDs
- **ChromaDB**: Supports `$in` operator (converted to ChromaDB format)
- Both databases store `document_id` in metadata for filtering

### Performance

- Filtering by `project_id` uses database index (fast)
- Filtering by `document_ids` uses vector metadata (efficient)
- No performance impact when filters are not used (backward compatible)
