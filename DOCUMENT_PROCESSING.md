# Document Processing (Queue-Based)

## How it works

Document upload and processing use a **proper queue**:

1. **Upload (fast)**  
   `POST /api/v1/documents/process` stores the file (local Volume or S3/Railway Buckets), creates a document row with `processing_status=pending`, enqueues a job to Redis, and returns immediately.

2. **Queue**  
   Redis + ARQ. Jobs are durable; if the worker restarts, jobs are not lost.

3. **Worker**  
   `python -m app.document_worker` runs an ARQ worker that:
   - Fetches jobs from Redis
   - Loads the file from storage (local path or S3)
   - Extracts text, runs LLM processing, chunks, creates embeddings
   - Upserts to vector DB (Pinecone)
   - Updates document status to `completed` or `failed`
   - Deletes the stored file on success

4. **Status**  
   Poll `GET /api/v1/documents` or `GET /api/v1/documents/{id}`. Each document has:
   - `processing_status`: `pending` | `processing` | `completed` | `failed`
   - `processing_error`: set when `processing_status === "failed"`

## Storage options

| Type | Use case | Config |
|------|----------|--------|
| **local** | Dev, Railway with shared Volume | `STORAGE_TYPE=local`, `UPLOAD_DIR=/data/uploads` |
| **s3** | Railway Storage Buckets (no shared Volume needed) | `STORAGE_TYPE=s3`, `S3_*` from Bucket credentials |

With **s3**, the API and worker can run on different machines; the worker fetches files from the bucket.

## Railway deployment

1. **Add Redis** – New → Database → Add Redis. Copy `REDIS_URL` to Backend and Worker.
2. **Storage** (choose one):
   - **Volume**: Create Volume, mount at `/data` on Backend and Worker. Set `UPLOAD_DIR=/data/uploads`, `STORAGE_TYPE=local`.
   - **Bucket**: Create Bucket, add S3 credentials to Backend and Worker. Set `STORAGE_TYPE=s3`.
3. **Backend** – Root Directory `backend`. Env: `DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_*`, `REDIS_URL`, storage vars.
4. **Document worker** – Same repo, Root Directory `backend`. Start Command: `python -m app.document_worker`. Same env as Backend (including `REDIS_URL` and storage vars).

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md#document-processing-on-railway) for details.

## Retry and reprocess

- **Retry** – `POST /api/v1/documents/{id}/retry` for stuck pending/failed documents. Requires the file to still exist (local or S3).
- **Reprocess** – `POST /api/v1/documents/reprocess` for documents that have content but no vectors.
- **Need reupload** – `GET /api/v1/documents/need-reupload` lists documents that must be re-uploaded (file lost).
