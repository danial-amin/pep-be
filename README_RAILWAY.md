# Railway Deployment - Important!

⚠️ **This repository has NO Dockerfile in the root directory.**

## Project Structure

- `backend/` - Backend API service (FastAPI/Python)
- `frontend/` - Frontend service (React/Node.js)

## Railway Configuration Required

When deploying on Railway, you **MUST** set the Root Directory for each service:

### Backend Service
- **Root Directory**: `backend`
- **Dockerfile Path**: `Dockerfile` (default)

### Frontend Service  
- **Root Directory**: `frontend`
- **Dockerfile Path**: `Dockerfile` (default)

## Setting Root Directory in Railway

1. Go to your service in Railway dashboard
2. Click **Settings** → **Source**
3. Set **Root Directory** to either `backend` or `frontend`
4. Save and redeploy

**If you don't set the Root Directory, Railway will fail to build because there's no Dockerfile in the root!**

See `RAILWAY_DEPLOYMENT.md` for complete deployment instructions.
