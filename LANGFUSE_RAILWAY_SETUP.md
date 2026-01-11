# Deploying Langfuse on Railway

This guide will help you deploy a self-hosted Langfuse instance on Railway for observability of your LLM calls.

## Quick Start (Recommended)

Railway has an official Langfuse template that makes deployment easy:

1. **Deploy from Template**
   - Visit: https://railway.app/template/langfuse
   - Click "Deploy Now"
   - Railway will automatically:
     - Create a PostgreSQL database
     - Deploy Langfuse
     - Configure the connection

2. **Get Your API Keys**
   - Once deployed, visit your Langfuse URL (Railway will provide it)
   - Sign up for the first admin account
   - Go to **Settings** → **API Keys**
   - Click **Create API Key**
   - Copy both the **Public Key** and **Secret Key**

3. **Configure Your PEP Backend**
   - Add to your backend `.env` file:
   ```bash
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-...  # From Langfuse dashboard
   LANGFUSE_SECRET_KEY=sk-lf-...  # From Langfuse dashboard
   LANGFUSE_HOST=https://your-langfuse-service.railway.app  # Your Railway URL
   ```

4. **Restart Your Backend**
   - Your backend will now send all LLM traces to Langfuse

## Manual Deployment (Alternative)

If you prefer to deploy manually:

### Step 1: Create Railway Project

1. Go to [Railway Dashboard](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"** or **"Empty Project"**

### Step 2: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically create and configure PostgreSQL
4. Note: Railway will provide a `DATABASE_URL` environment variable automatically

### Step 3: Deploy Langfuse

**Option A: Using Railway Template (Easiest)**
- Click **"+ New"** → **"Template"**
- Search for "Langfuse"
- Click **"Deploy"**

**Option B: Using Dockerfile**

1. Click **"+ New"** → **"GitHub Repo"** or **"Empty Service"**
2. If using GitHub:
   - Point to your repo
   - Set root directory to `langfuse-railway/`
3. If using Empty Service:
   - Railway will detect the Dockerfile in `langfuse-railway/`
   - Or upload the `langfuse-railway` directory

### Step 4: Configure Environment Variables

In your Langfuse service, go to **"Variables"** and add:

```bash
# Database (Railway auto-provides this if using their PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}
# Or manually: postgresql://postgres:password@postgres.railway.internal:5432/railway

# Required: Generate these secrets
NEXTAUTH_SECRET=<generate-with-openssl-rand-base64-32>
NEXTAUTH_URL=${{RAILWAY_PUBLIC_DOMAIN}}
SALT=<generate-with-openssl-rand-base64-32>
```

**Generate Secrets:**
```bash
# Generate NEXTAUTH_SECRET
openssl rand -base64 32

# Generate SALT
openssl rand -base64 32
```

**Note:** Railway provides `${{RAILWAY_PUBLIC_DOMAIN}}` automatically, or you can use your custom domain.

### Step 5: Deploy and Access

1. Railway will automatically deploy Langfuse
2. Once deployed, Railway will provide a public URL
3. Visit the URL and sign up for the first admin account
4. This account will have full admin privileges

### Step 6: Get API Keys

1. In Langfuse dashboard, go to **Settings** → **API Keys**
2. Click **"Create API Key"**
3. Give it a name (e.g., "PEP Backend")
4. Copy both keys:
   - **Public Key** (starts with `pk-lf-`)
   - **Secret Key** (starts with `sk-lf-`)

### Step 7: Connect Your PEP Backend

Update your backend `.env` file:

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...  # Your public key
LANGFUSE_SECRET_KEY=sk-lf-...   # Your secret key
LANGFUSE_HOST=https://your-langfuse.railway.app  # Your Railway URL
```

Restart your backend service.

## Verification

1. **Check Langfuse Dashboard**
   - Visit your Langfuse URL
   - You should see the dashboard

2. **Test Tracing**
   - Make a request to your PEP backend that triggers an LLM call
   - Go to Langfuse dashboard → **Traces**
   - You should see traces appearing

3. **Check Backend Logs**
   - Look for: `"Langfuse client initialized successfully"`
   - If you see warnings about Langfuse keys, check your configuration

## Troubleshooting

### Langfuse not receiving traces

1. **Check Environment Variables**
   ```bash
   # In your backend, verify:
   echo $LANGFUSE_ENABLED      # Should be "true"
   echo $LANGFUSE_PUBLIC_KEY   # Should start with "pk-lf-"
   echo $LANGFUSE_SECRET_KEY   # Should start with "sk-lf-"
   echo $LANGFUSE_HOST         # Should be your Railway URL
   ```

2. **Check Backend Logs**
   - Look for Langfuse initialization messages
   - Check for any error messages about Langfuse

3. **Verify API Keys**
   - Go to Langfuse dashboard → Settings → API Keys
   - Make sure the keys are active
   - Try creating new keys if needed

### Database Connection Issues

1. **Check PostgreSQL Service**
   - In Railway, verify PostgreSQL is running
   - Check the `DATABASE_URL` is correct

2. **Verify Connection String**
   - Should be: `postgresql://user:password@host:port/database`
   - Railway provides this automatically if using their PostgreSQL service

### Can't Access Langfuse Dashboard

1. **Check Railway Deployment**
   - Verify the service is deployed and running
   - Check Railway logs for errors

2. **Verify Public URL**
   - Railway provides a public domain automatically
   - Or configure a custom domain in Railway settings

3. **Check Environment Variables**
   - `NEXTAUTH_URL` should match your public URL
   - `DATABASE_URL` should be correct

## Cost Estimation

Railway pricing (as of 2024):
- **PostgreSQL**: ~$5/month for starter plan
- **Langfuse Service**: ~$5/month for starter plan
- **Total**: ~$10/month for self-hosted observability

This is often cheaper than cloud Langfuse for high-volume usage.

## Using Langfuse for Multiple Projects

**Yes!** You can use the same Langfuse instance for multiple different projects. This is one of Langfuse's key features.

### Setting Up Multiple Projects

1. **Create Projects in Langfuse**
   - Go to Langfuse dashboard → **Projects**
   - Click **"New Project"**
   - Create separate projects for:
     - PEP (Persona Generator)
     - Your other LLM project
     - Any other projects you have

2. **Get API Keys for Each Project**
   - For each project, go to **Settings** → **API Keys**
   - Create a new API key for that project
   - Each project can have multiple API keys
   - Use different keys for different services/environments

3. **Configure Each Application**
   
   **For PEP Backend:**
   ```bash
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-pep-project-...
   LANGFUSE_SECRET_KEY=sk-lf-pep-project-...
   LANGFUSE_HOST=https://your-langfuse.railway.app
   ```
   
   **For Your Other LLM Project:**
   ```bash
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-other-project-...
   LANGFUSE_SECRET_KEY=sk-lf-other-project-...
   LANGFUSE_HOST=https://your-langfuse.railway.app  # Same instance!
   ```

### Benefits of Multi-Project Setup

- **Centralized Observability**: One dashboard for all your LLM projects
- **Cost Efficiency**: One Langfuse instance for all projects
- **Easy Comparison**: Compare performance across different projects
- **Unified Monitoring**: Set up alerts and monitoring for all projects
- **Project Isolation**: Each project's data is separate and secure

### Project Organization Tips

1. **Naming Convention**
   - Use clear project names: "PEP - Persona Generator", "Chatbot API", etc.
   - Add environment suffixes if needed: "PEP - Production", "PEP - Staging"

2. **API Key Management**
   - Create separate keys for production/staging
   - Rotate keys periodically
   - Use descriptive key names

3. **Filtering in Dashboard**
   - Use the project filter to view traces for specific projects
   - Compare metrics across projects
   - Export data per project

### Example: Multiple Projects Setup

```
Langfuse Instance (Railway)
├── Project: PEP - Persona Generator
│   ├── API Key 1: PEP Backend (Production)
│   ├── API Key 2: PEP Backend (Staging)
│   └── Traces: All persona generation calls
│
├── Project: Customer Support Chatbot
│   ├── API Key 1: Chatbot API
│   └── Traces: All chatbot interactions
│
└── Project: Document Analysis Service
    ├── API Key 1: Analysis API
    └── Traces: All document processing calls
```

Each project is completely isolated - traces, costs, and settings are separate.

## Next Steps

Once Langfuse is set up:

1. **Monitor Traces**
   - View all LLM calls in the Langfuse dashboard
   - Filter by project, model, or time range
   - Switch between projects to see different applications

2. **Debug Failures**
   - See detailed error messages for failed calls
   - View input/output for each generation
   - Filter errors by project

3. **Track Costs**
   - Monitor token usage across all calls
   - See costs per project or operation
   - Compare costs between projects

4. **Set Up Alerts** (Optional)
   - Configure alerts for high error rates
   - Monitor token usage limits
   - Set project-specific alerts

5. **Add More Projects**
   - Create new projects as needed
   - Each new project gets its own API keys
   - All projects share the same Langfuse instance

## Resources

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Projects Guide](https://langfuse.com/docs/projects)
- [Railway Documentation](https://docs.railway.app)
- [Langfuse Self-Hosting Guide](https://langfuse.com/docs/deployment/self-host)
