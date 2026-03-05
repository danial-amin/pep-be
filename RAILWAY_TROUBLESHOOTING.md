# Railway Deployment Failure Analysis & Fixes

This document explains the most likely causes of frontend and backend deployment failures on Railway and how to fix them.

---

## 1. Root directory not set (most common)

**Symptom:** Build fails with errors like:
- `Dockerfile not found`
- `COPY failed: file not found in build context`
- `"/alembic": not found` or `"/app/requirements.txt": not found`
- Frontend builds a Python app or backend builds fail with wrong paths

**Cause:** Railway is building from the **repository root** instead of the service directory. Your app is a monorepo: backend lives in `backend/`, frontend in `frontend/`. Each service must use its own folder as the build root.

**Fix:**

| Service  | Root Directory (set in Railway dashboard) |
|----------|-------------------------------------------|
| Backend  | `backend`                                 |
| Frontend | `frontend`                                |

**Steps:**
1. Railway Dashboard → your **Backend** service → **Settings** → **Source**
2. Set **Root Directory** to `backend` (no leading/trailing slash). Save.
3. Railway Dashboard → your **Frontend** service → **Settings** → **Source**
4. Set **Root Directory** to `frontend`. Save.
5. Trigger a **new deployment** for each service (Deployments → Redeploy).

If the option is missing or doesn’t stick, delete the service and re-add it from the same repo, then set Root Directory **before** the first build.

---

## 2. Railway config file path (railway.toml)

**Symptom:** Railway ignores your `railway.toml` (e.g. still uses Nixpacks/Railpack instead of Dockerfile, or wrong Dockerfile path).

**Cause:** Railway’s docs state: *“The Railway Config File does not follow the Root Directory path. You have to specify the absolute path for the railway.toml file.”* So with Root Directory set to `backend` or `frontend`, Railway may still look for config at the repo root and never see `backend/railway.toml` or `frontend/railway.toml`.

**Fix:** In the dashboard, set the **config file path** (e.g. “Railway config path” or “Config file”) to the path **from the repo root**:

| Service  | Config file path (from repo root) |
|----------|------------------------------------|
| Backend  | `backend/railway.toml`             |
| Frontend | `frontend/railway.toml`            |

Where to set it: **Settings** → **Source** (or **Build**) and look for “Config file”, “Railway config”, or “railway.toml path”. If you can’t find it, ensure at least **Root Directory** is set (above); some setups work with only that.

---

## 3. Root Dockerfile confusion

**Symptom:** Frontend service builds a Python/backend image, or both services build the same image.

**Cause:** There is a **Dockerfile in the repo root** that builds the **backend**. If the frontend service does **not** have Root Directory set to `frontend`, Railway may use the root Dockerfile for it too, so the “frontend” deployment is actually the backend.

**Fix:** For the **Frontend** service, **Root Directory** must be `frontend` so Railway uses `frontend/Dockerfile` (Node + nginx), not the root Dockerfile.

---

## 4. Backend: missing or wrong build context

**Symptom:** Errors like `COPY failed: file not found`, or `requirements.txt` / `alembic` not found.

**Cause:** Backend Dockerfile expects to be run with build context = `backend/`. It uses paths like `COPY ./app`, `COPY ./alembic`, `COPY ./default_personas/`. If Root Directory is not `backend`, those paths don’t exist in the context.

**Fix:** Set Root Directory to `backend` (see §1). Do not use the root Dockerfile for the backend unless you intentionally build from repo root and use paths like `./backend/app` (your root Dockerfile already does this; for consistency, using `backend/` as root is recommended).

---

## 5. Frontend: build or runtime failures

**Symptom:** Frontend build fails during `npm run build` (e.g. TypeScript or Vite errors), or container exits on start.

**Cause:**  
- Build: missing deps, TS errors, or wrong Node version.  
- Runtime: missing `nginx.conf` or `start-nginx.sh`, or PORT not respected.

**Checks:**
- Root Directory = `frontend` so that `frontend/nginx.conf` and `frontend/start-nginx.sh` are in the build context (they are in the repo).
- `frontend/Dockerfile` uses `node:20-alpine` and `npm run build`; ensure the app builds locally with `npm run build` in `frontend/`.
- Railway sets `PORT`; your `start-nginx.sh` uses `PORT` and adjusts nginx. No extra env vars are required for PORT.

---

## 6. Health checks

- **Backend:** `railway.toml` uses `healthcheckPath = "/healthcheck"`. Your app exposes `/healthcheck` and `/health` in `backend/app/main.py`. No change needed if Root Directory is `backend`.
- **Frontend:** `healthcheckPath = "/"`. Served by nginx. Fine as long as the frontend is built from `frontend/` and nginx runs.

---

## 7. Environment variables

**Backend (required for a working deploy):**
- `DATABASE_URL` (from Railway Postgres)
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `PINECONE_ENVIRONMENT`

**Frontend:**
- `VITE_API_URL` = backend API base URL (e.g. `https://your-backend.up.railway.app/api/v1`). Used at build time in the Dockerfile; set in Railway **Variables** for the frontend service.

If any required backend env var is missing, the app can crash on startup; check **Logs** in Railway for the failing service.

---

## Quick checklist

- [ ] **Backend** Root Directory = `backend`
- [ ] **Frontend** Root Directory = `frontend`
- [ ] Config file path (if available) = `backend/railway.toml` and `frontend/railway.toml`
- [ ] Backend env: `DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_*`
- [ ] Frontend env: `VITE_API_URL` = backend URL + `/api/v1`
- [ ] Redeploy both services after changing Root Directory or config path
- [ ] Run DB migrations: `railway run alembic upgrade head` (with backend service linked)

---

## Getting exact error messages

1. **Build failures:** Railway Dashboard → service → **Deployments** → latest deployment → **Build logs**. Look for the first red error (e.g. COPY, missing file, or wrong path).
2. **Runtime failures:** Same deployment → **Deploy** or **Logs** tab. Look for Python tracebacks, “Address already in use”, or missing env vars.

If you have a specific error line (e.g. “COPY failed” or “Dockerfile not found”), set Root Directory and config path as above, then redeploy. If it still fails, use the exact message from the build or runtime logs to narrow it down (e.g. missing file name or path).
