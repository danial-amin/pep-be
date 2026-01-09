# Railway Deployment Guide

This guide will help you deploy the PEP (Persona Generator) application on Railway.

## Overview

Railway deployment requires three services:
1. **Backend API** - FastAPI application
2. **Frontend** - React application served via nginx
3. **PostgreSQL Database** - Railway managed PostgreSQL service

## Prerequisites

- A Railway account (sign up at [railway.app](https://railway.app))
- Railway CLI installed (optional, but recommended)
- Your API keys:
  - OpenAI API Key
  - Pinecone API Key (if using Pinecone)

## Deployment Steps

### Step 1: Create a New Project on Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo" (recommended) or "Empty Project"

### Step 2: Add PostgreSQL Database

1. In your Railway project, click "New" → "Database" → "Add PostgreSQL"
2. Railway will automatically create a PostgreSQL database
3. Note the connection details (you'll need the `DATABASE_URL`)

### Step 3: Deploy Backend API

1. In your Railway project, click "New" → "GitHub Repo" (or "Empty Service")
2. Select your repository
3. Configure the service:
   - **Root Directory**: Leave empty (root)
   - **Dockerfile Path**: `Dockerfile.backend` (explicitly set this)
   - **Build Command**: (auto-detected)
   - **Start Command**: (auto-detected from Dockerfile)
   
**Note**: The backend uses `Dockerfile.backend` to clearly distinguish it from the frontend service.

#### Environment Variables for Backend

Add these environment variables in the Railway service settings:

**Required:**
```
DATABASE_URL=<from PostgreSQL service>
OPENAI_API_KEY=<your-openai-api-key>
PINECONE_API_KEY=<your-pinecone-api-key>
PINECONE_ENVIRONMENT=<your-pinecone-environment>
```

**Optional (with defaults):**
```
VECTOR_DB_TYPE=pinecone
PINECONE_INDEX_NAME=pep-documents
ENVIRONMENT=production
CORS_ORIGINS=<your-frontend-url>
LOG_LEVEL=INFO
```

**Getting DATABASE_URL from Railway:**
- Click on your PostgreSQL service
- Go to the "Variables" tab
- Copy the `DATABASE_URL` value
- Paste it into your backend service's environment variables

### Step 4: Deploy Frontend

1. In your Railway project, click "New" → "GitHub Repo"
2. Select the same repository
3. **IMPORTANT**: Configure the service settings:
   - Go to the service → **Settings** → **Source**
   - Set **Root Directory**: `frontend` (this is critical - must be set to `frontend`)
   - **Dockerfile Path**: `Dockerfile.frontend` (explicitly set this)
   - **Build Command**: (auto-detected)
   - **Start Command**: (auto-detected)
   
**Note**: The frontend uses `Dockerfile.frontend` to clearly distinguish it from the backend service.

**⚠️ Critical**: If you don't set the Root Directory to `frontend`, Railway will try to build from the root directory and use `Dockerfile.backend` (the backend Dockerfile), which will fail because it's looking for Python dependencies instead of Node.js.

#### Environment Variables for Frontend

Add this environment variable **before the first deployment**:

```
VITE_API_URL=<your-backend-api-url>/api/v1
```

**Getting Backend URL:**
- After deploying the backend, Railway will provide a public URL
- It will look like: `https://your-backend-service.up.railway.app`
- Use this URL in `VITE_API_URL`: `https://your-backend-service.up.railway.app/api/v1`

**Important:** The `VITE_API_URL` is used at build time, so you need to:
1. Set the environment variable first
2. Then trigger a new deployment (Railway will rebuild with the new value)

Alternatively, you can set it as a build argument in Railway's service settings under "Settings" → "Variables" → "Build Arguments".

### Step 5: Configure CORS

Update the backend's `CORS_ORIGINS` environment variable to include your frontend URL:

```
CORS_ORIGINS=https://your-frontend-service.up.railway.app
```

Or if you want to allow all origins (not recommended for production):
```
CORS_ORIGINS=*
```

### Step 6: Run Database Migrations

After the backend is deployed, you need to run Alembic migrations:

1. Open the backend service in Railway
2. Go to the "Deployments" tab
3. Click on the latest deployment
4. Open the "Logs" tab
5. Click "Run Command" or use Railway CLI:

```bash
railway run alembic upgrade head
```

Or using Railway CLI:
```bash
railway link
railway run --service <backend-service-name> alembic upgrade head
```

## Railway CLI Setup (Optional)

If you prefer using the CLI:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Deploy
railway up

# Run migrations
railway run alembic upgrade head

# View logs
railway logs
```

## Environment Variables Reference

### Backend Service

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | - |
| `OPENAI_API_KEY` | Yes | OpenAI API key | - |
| `PINECONE_API_KEY` | Yes | Pinecone API key | - |
| `PINECONE_ENVIRONMENT` | Yes | Pinecone environment/region | - |
| `PINECONE_INDEX_NAME` | No | Pinecone index name | `pep-documents` |
| `VECTOR_DB_TYPE` | No | Vector DB type (`pinecone` or `chroma`) | `pinecone` |
| `ENVIRONMENT` | No | Environment (`development` or `production`) | `development` |
| `CORS_ORIGINS` | No | CORS allowed origins (comma-separated) | `*` |
| `LOG_LEVEL` | No | Logging level | `INFO` |

### Frontend Service

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `VITE_API_URL` | Yes | Backend API URL | - |

## Custom Domains

Railway provides default domains, but you can add custom domains:

1. Go to your service settings
2. Click "Settings" → "Networking"
3. Add your custom domain
4. Update DNS records as instructed

## Monitoring and Logs

- **Logs**: View real-time logs in the Railway dashboard under each service
- **Metrics**: Railway provides basic metrics (CPU, Memory, Network)
- **Health Checks**: The backend has a `/health` endpoint that Railway can monitor

## Troubleshooting

### Backend won't start

1. Check logs in Railway dashboard
2. Verify all required environment variables are set
3. Ensure `DATABASE_URL` is correctly formatted
4. Check that migrations have been run

### Frontend can't connect to backend

1. Verify `VITE_API_URL` is set correctly
2. Check backend CORS settings
3. Ensure backend service is running and healthy
4. Check Railway service URLs are correct

### Database connection errors

1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL service is running
3. Ensure database migrations have been run
4. Check network connectivity between services

### Build failures

1. Check build logs for specific errors
2. Verify Dockerfile syntax
3. Ensure all required files are present
4. Check `.railwayignore` isn't excluding necessary files

### Frontend build error: "COPY requirements.txt" not found

**Symptom**: Frontend build fails with error about `requirements.txt` not found

**Cause**: Railway is building from the root directory instead of the `frontend` directory

**Solution**:
1. Go to your frontend service in Railway dashboard
2. Click **Settings** → **Source**
3. Set **Root Directory** to: `frontend`
4. Save and redeploy

The frontend Dockerfile doesn't use `requirements.txt` (it's a Node.js app), so this error means Railway is using the wrong Dockerfile from the root directory.

## Cost Optimization

- Railway provides a free tier with $5 credit monthly
- PostgreSQL: Use Railway's managed PostgreSQL (included in free tier)
- Consider using Railway's sleep feature for development environments
- Monitor usage in the Railway dashboard

## Production Checklist

- [ ] All environment variables configured
- [ ] Database migrations run
- [ ] CORS configured for production frontend URL
- [ ] Custom domains configured (if needed)
- [ ] Health checks enabled
- [ ] Logging configured
- [ ] Backup strategy for database
- [ ] Monitoring set up

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
