# Pinecone Setup Guide

## Why Pinecone?

✅ **Free Tier Available**: 100K vectors, perfect for getting started  
✅ **Managed Service**: No infrastructure to maintain  
✅ **Scalable**: Handles large documents effortlessly  
✅ **Production Ready**: Used by many companies  
✅ **Cost Effective**: Free tier covers most use cases  

## Quick Setup

### 1. Get Pinecone API Key

1. Go to [https://www.pinecone.io/](https://www.pinecone.io/)
2. Sign up for a free account
3. Create a new project
4. Copy your API key from the dashboard
5. Note your environment (e.g., `us-east-1-aws` or `gcp-starter`)

### 2. Configure Environment

Add to your `.env` file:

```env
# Vector Database
VECTOR_DB_TYPE=pinecone

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-east-1-aws  # or "gcp-starter" for free tier
PINECONE_INDEX_NAME=pep-documents
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Application

The system will automatically:
- Create the Pinecone index if it doesn't exist
- Use serverless spec (free tier compatible)
- Configure for `text-embedding-3-large` (3072 dimensions)

```bash
docker-compose up -d
```

## Free Tier Limits

- **100,000 vectors** (plenty for documents)
- **Serverless** deployment
- **No credit card required**
- Perfect for development and small to medium projects

## How It Works

1. **Document Upload**: Documents are chunked and embedded
2. **Storage**: Embeddings stored in Pinecone (free tier = 100K vectors)
3. **Retrieval**: Semantic search finds relevant chunks
4. **Cost**: Only embedding API calls cost money (OpenAI), Pinecone storage is free

## Migration from ChromaDB

If you were using ChromaDB:

1. Set `VECTOR_DB_TYPE=pinecone` in `.env`
2. Add Pinecone credentials
3. Restart the application
4. Re-upload documents (they'll be stored in Pinecone)

**Note**: ChromaDB data won't migrate automatically. You'll need to re-process documents.

## Index Management

The index is created automatically on first use. To manage it manually:

```python
from app.core.vector_db_pinecone import pinecone_vector_db

# List indexes
indexes = pinecone_vector_db.client.list_indexes()

# Delete index (if needed)
pinecone_vector_db.client.delete_index("pep-documents")
```

## Troubleshooting

### "PINECONE_API_KEY is required"
- Make sure you've set `PINECONE_API_KEY` in your `.env` file
- Restart the application after adding the key

### "Index creation failed"
- Check your Pinecone environment/region
- Free tier uses serverless (automatic)
- Make sure your API key has proper permissions

### "Dimension mismatch"
- The system uses 3072 dimensions for `text-embedding-3-large`
- If you change embedding models, update the dimension in `vector_db_pinecone.py`

## Cost Comparison

### ChromaDB (Self-hosted)
- ❌ Requires server (Docker container)
- ❌ Maintenance overhead
- ✅ Free (but you pay for hosting)

### Pinecone (Free Tier)
- ✅ Managed service
- ✅ No infrastructure
- ✅ 100K vectors free
- ✅ Auto-scaling
- ✅ Production-ready

## Production Deployment

For production:
1. Upgrade to Pinecone paid plan if needed (more vectors)
2. Use dedicated index (not serverless) for better performance
3. Set up monitoring in Pinecone dashboard
4. Configure backup/retention policies

## Support

- Pinecone Docs: https://docs.pinecone.io/
- Free Tier Info: https://www.pinecone.io/pricing/

