# Railway Quick Start Checklist

Use this checklist for a quick deployment on Railway.

## Pre-Deployment

- [ ] Railway account created
- [ ] OpenAI API key ready
- [ ] Pinecone API key ready
- [ ] GitHub repository connected to Railway

## Deployment Steps

### 1. Create Project
- [ ] New Project → Deploy from GitHub repo
- [ ] Select your repository

### 2. Add PostgreSQL
- [ ] New → Database → Add PostgreSQL
- [ ] Copy `DATABASE_URL` from Variables tab

### 3. Deploy Backend
- [ ] New → GitHub Repo → Select repository
- [ ] Root Directory: (leave empty)
- [ ] Set environment variables:
  - [ ] `DATABASE_URL` = (from PostgreSQL service)
  - [ ] `OPENAI_API_KEY` = (your key)
  - [ ] `PINECONE_API_KEY` = (your key)
  - [ ] `PINECONE_ENVIRONMENT` = (your region)
  - [ ] `ENVIRONMENT` = `production`
- [ ] Wait for deployment to complete
- [ ] Copy backend URL (e.g., `https://xxx.up.railway.app`)

### 4. Deploy Frontend
- [ ] New → GitHub Repo → Select same repository
- [ ] Root Directory: `frontend`
- [ ] Set environment variable:
  - [ ] `VITE_API_URL` = `{backend-url}/api/v1`
- [ ] Wait for deployment to complete
- [ ] Copy frontend URL

### 5. Configure CORS
- [ ] Go to Backend service → Variables
- [ ] Update `CORS_ORIGINS` = `{frontend-url}`

### 6. Run Migrations
- [ ] Backend service → Deployments → Latest → Run Command
- [ ] Command: `alembic upgrade head`
- [ ] Or use Railway CLI: `railway run --service backend alembic upgrade head`

### 7. Verify
- [ ] Backend health: `{backend-url}/health`
- [ ] Frontend loads correctly
- [ ] Test API connection from frontend

## Environment Variables Summary

### Backend
```
DATABASE_URL=<from-postgres-service>
OPENAI_API_KEY=<your-key>
PINECONE_API_KEY=<your-key>
PINECONE_ENVIRONMENT=<your-region>
PINECONE_INDEX_NAME=pep-documents
ENVIRONMENT=production
CORS_ORIGINS=<frontend-url>
```

### Frontend
```
VITE_API_URL=<backend-url>/api/v1
```

## Troubleshooting

- **Backend won't start**: Check logs, verify DATABASE_URL format
- **Frontend can't connect**: Verify VITE_API_URL and CORS_ORIGINS
- **Database errors**: Run migrations with `alembic upgrade head`

## Next Steps

- [ ] Set up custom domains (optional)
- [ ] Configure monitoring
- [ ] Set up backups
- [ ] Review Railway usage and costs
