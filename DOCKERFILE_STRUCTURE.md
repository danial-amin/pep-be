# Dockerfile Structure

This project uses separate Dockerfiles for backend and frontend services to make Railway deployment clearer.

## File Structure

```
pep-be/
├── Dockerfile.backend          # Backend API (FastAPI/Python)
├── frontend/
│   └── Dockerfile.frontend     # Frontend (React/Node.js)
└── docker-compose.yml          # Local development (references both)
```

## Dockerfiles

### Backend: `Dockerfile.backend`
- **Location**: Root directory
- **Purpose**: FastAPI Python backend
- **Base Image**: `python:3.11-slim`
- **Port**: 8080 (or Railway's PORT env var)
- **Used by**: 
  - Railway backend service (root directory)
  - Local development via `docker-compose.yml`

### Frontend: `Dockerfile.frontend`
- **Location**: `frontend/` directory
- **Purpose**: React frontend with nginx
- **Base Image**: `node:20-alpine` (build) + `nginx:alpine` (production)
- **Port**: 80
- **Used by**: 
  - Railway frontend service (with Root Directory: `frontend`)
  - Local development via `docker-compose.yml`

## Railway Configuration

### Backend Service
- **Root Directory**: (empty/root)
- **Dockerfile Path**: `Dockerfile.backend`
- **Railway Config**: `railway.toml` (root)

### Frontend Service
- **Root Directory**: `frontend`
- **Dockerfile Path**: `Dockerfile.frontend`
- **Railway Config**: `frontend/railway.toml`

## Why Separate Dockerfiles?

1. **Clarity**: Makes it immediately clear which Dockerfile is for which service
2. **Railway**: Prevents Railway from auto-detecting the wrong Dockerfile
3. **Maintenance**: Easier to manage and update each service independently
4. **Documentation**: Self-documenting structure

## Local Development

Both Dockerfiles are referenced in `docker-compose.yml`:
- Backend: `dockerfile: Dockerfile.backend`
- Frontend: `dockerfile: Dockerfile.frontend`

This ensures consistency between local development and Railway deployment.
