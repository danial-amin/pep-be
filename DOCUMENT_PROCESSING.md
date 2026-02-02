# Document Processing (Background, No Celery)

## How it works

Document upload and processing are **decoupled**:

1. **Upload (fast)**  
   `POST /api/v1/documents/process` stores the file on disk, creates a document row with `processing_status=pending`, and returns immediately. The client gets a 201 with `processing_status: "pending"`.

2. **Processing (background)**  
   Heavy work (text extraction, LLM processing, chunking, embeddings, vector DB) runs **in-process** via FastAPI’s **BackgroundTasks**, not Celery or a separate worker.  
   - After the response is sent, the same process runs `DocumentService.process_document_background(document_id)`.  
   - The task uses its own DB session, reads the file from disk, runs the pipeline, updates the document (`processing_status=completed` or `failed`), then deletes the file.

3. **Status**  
   The frontend polls `GET /api/v1/documents` (or `GET /api/v1/documents/{id}`). Each document has:
   - `processing_status`: `pending` | `processing` | `completed` | `failed`
   - `processing_error`: set when `processing_status === "failed"`

So you **do not need Celery or Redis**. Everything runs inside the FastAPI process.

## Trade-offs

| Aspect | In-process (current) | Celery / worker |
|--------|----------------------|------------------|
| Setup | None | Redis + worker process |
| After server restart | Pending docs re-queued on startup (see below) | Survives restarts if broker persists |
| Scale | Limited by one process | Can scale workers |
| Retries | None built-in | Configurable retries |

For moderate upload volume and single-instance deployment, in-process background tasks are usually enough.

## After a server restart

If the server stops while some documents are still `pending`, those rows remain in the DB with `file_path` set. On **startup**, the app:

1. Selects all documents with `processing_status=pending` and non-null `file_path`.
2. Schedules `process_document_background(doc.id)` for each (via `asyncio.create_task`).

So pending documents are resumed automatically after deploy or restart; no separate queue or broker is required.

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
