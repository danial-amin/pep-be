# Dockerfile Structure

This project uses a clear folder structure with separate `backend/` and `frontend/` directories, each with their own `Dockerfile`. This prevents Railway from auto-detecting the wrong Dockerfile.

## File Structure

```
pep-be/
├── backend/
│   ├── Dockerfile              # Backend API (FastAPI/Python)
│   ├── railway.toml            # Railway config for backend
│   ├── app/                     # Application code
│   ├── alembic/                 # Database migrations
│   └── default_personas/        # Default persona data
├── frontend/
│   ├── Dockerfile              # Frontend (React/Node.js)
│   ├── railway.toml            # Railway config for frontend
│   └── src/                     # Frontend source code
└── docker-compose.yml          # Local development (references both)
```

## Dockerfiles

### Backend: `backend/Dockerfile`
- **Location**: `backend/` directory
- **Purpose**: FastAPI Python backend
- **Base Image**: `python:3.11-slim`
- **Port**: 8080 (or Railway's PORT env var)
- **Used by**: 
  - Railway backend service (with Root Directory: `backend`)
  - Local development via `docker-compose.yml`

### Frontend: `frontend/Dockerfile`
- **Location**: `frontend/` directory
- **Purpose**: React frontend with nginx
- **Base Image**: `node:20-alpine` (build) + `nginx:alpine` (production)
- **Port**: 80
- **Used by**: 
  - Railway frontend service (with Root Directory: `frontend`)
  - Local development via `docker-compose.yml`

## Railway Configuration

### Backend Service
- **Root Directory**: `backend` (must be set explicitly)
- **Dockerfile Path**: `Dockerfile` (default, found in backend directory)
- **Railway Config**: `backend/railway.toml`

### Frontend Service
- **Root Directory**: `frontend` (must be set explicitly)
- **Dockerfile Path**: `Dockerfile` (default, found in frontend directory)
- **Railway Config**: `frontend/railway.toml`

## Why This Structure?

1. **No Auto-Detection Issues**: Railway won't find a Dockerfile in the root, so it won't auto-detect the wrong one
2. **Clear Separation**: Backend and frontend are completely separated
3. **Self-Documenting**: The folder structure makes it obvious which service is which
4. **Easy Maintenance**: Each service is independent and easy to update
5. **Standard Dockerfile Names**: Both use `Dockerfile` (standard convention) in their respective directories

## Local Development

Both Dockerfiles are referenced in `docker-compose.yml`:
- Backend: `context: ./backend`, `dockerfile: Dockerfile`
- Frontend: `context: ./frontend`, `dockerfile: Dockerfile`

This ensures consistency between local development and Railway deployment.
