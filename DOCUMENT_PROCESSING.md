# Document Processing (Background, No Celery)

## How it works

Document upload and processing are **decoupled**:

1. **Upload (fast)**  
   `POST /api/v1/documents/process` stores the file on disk (or a shared Volume on Railway), creates a document row with `processing_status=pending`, and returns immediately. The client gets a 201 with `processing_status: "pending"`.

2. **Processing (background)**  
   Heavy work (text extraction, LLM processing, chunking, embeddings, vector DB) can run in two ways:
   - **In-process**: FastAPI’s **BackgroundTasks** run `DocumentService.process_document_background(document_id)` after the response is sent. This works as long as the same process stays alive.
   - **Worker (Railway)**: A separate process runs `python -m app.document_worker`, which polls for `pending` documents and processes them. Use this on Railway so uploads are processed even when the web process restarts or doesn’t finish BackgroundTasks.

3. **Status**  
   The frontend polls `GET /api/v1/documents` (or `GET /api/v1/documents/{id}`). Each document has:
   - `processing_status`: `pending` | `processing` | `completed` | `failed`
   - `processing_error`: set when `processing_status === "failed"`

You **do not need Celery or Redis**. Use the in-process background task locally, and the **document worker** on Railway (see below).

## Railway deployment (recommended)

On Railway, the web container’s filesystem is ephemeral and the process may restart before BackgroundTasks finish, so **pending documents often never get processed**. To fix this:

1. **Railway Volume** – Create a Volume and mount it at `/data` on both the **Backend** and a **Document worker** service.
2. **Backend** – Set `UPLOAD_DIR=/data/uploads` so uploads are stored on the Volume.
3. **Document worker** – New service, same repo, Root Directory `backend`, Start Command: `python -m app.document_worker`. Mount the same Volume at `/data` and set `UPLOAD_DIR=/data/uploads`.

The worker polls every 20 seconds (configurable via `DOCUMENT_WORKER_POLL_SECONDS`), picks up pending documents, and processes them into vectors. No Redis or Celery. See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md#document-processing-on-railway) for step-by-step setup.

## Trade-offs

| Aspect | In-process (current) | Document worker (Railway) | Celery / worker |
|--------|-----------------------|----------------------------|------------------|
| Setup | None | Volume + second service | Redis + worker process |
| After server restart | Pending re-queued on startup if file still on disk | Worker keeps polling; file on Volume | Survives if broker persists |
| Scale | One process | One worker + web | Can scale workers |

For **local/dev**, in-process BackgroundTasks are enough. For **Railway**, use the document worker + Volume so uploads are always processed.

## After a server restart (without worker)

If you don’t run the worker and the server stops while some documents are still `pending`, those rows remain in the DB with `file_path` set. On **startup**, the app:

1. Selects all documents with `processing_status=pending` and non-null `file_path`.
2. Schedules `process_document_background(doc.id)` for each (via `asyncio.create_task`).

So pending documents are resumed **only if the file still exists** (e.g. same container, or uploads on a Volume). On Railway without a Volume, the file is usually gone after a restart, so processing will fail with “Stored file not found”. Use a Volume + worker for reliable processing on Railway.

## Frontend: how to see if a document is processed

- **List view**  
  Each row shows a status badge: **Queued** (pending), **Processing** (with spinner), **Ready** (completed), or **Failed** (with error).

- **Banner**  
  When any document is pending or processing, a blue banner appears: “X document(s) being processed. List updates every few seconds.” The list is polled every 3 seconds until none are pending/processing.

- **Refresh**  
  The list header has a refresh button; you can also refresh the page to refetch.

- **API**  
  `GET /api/v1/documents` returns `processing_status` and `processing_error` for each document so the UI can always show current state.

## Optional: moving to Celery later

If you later need retries, multiple workers, or decoupling from the web process:

1. Add Redis (or another broker) and Celery.
2. Replace `background_tasks.add_task(DocumentService.process_document_background, document.id)` with a Celery task (e.g. `process_document_task.delay(document.id)`).
3. Implement the same pipeline inside that task and update the document row when done.
4. Keep the same API and `processing_status` / `processing_error` so the frontend stays unchanged.

The current design (pending row + background processing) is compatible with that migration.
