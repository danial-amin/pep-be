# Langfuse Self-Hosted on Railway

This directory contains the configuration files needed to deploy Langfuse on Railway.

## Quick Deploy

### Option 1: Deploy from Railway Template (Recommended)

1. Go to [Railway Langfuse Template](https://railway.app/template/langfuse)
2. Click "Deploy Now"
3. Railway will automatically set up Langfuse with PostgreSQL

### Option 2: Manual Deployment

1. **Create a new Railway project**
   - Go to [Railway Dashboard](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo" or "Empty Project"

2. **Add PostgreSQL Service**
   - In your Railway project, click "+ New"
   - Select "Database" → "PostgreSQL"
   - Railway will automatically create a PostgreSQL instance
   - Note the connection details (you'll need them for Langfuse)

3. **Deploy Langfuse**
   - Click "+ New" → "GitHub Repo" (or "Empty Service")
   - If using GitHub, point to this directory or use the Dockerfile
   - If using Empty Service, Railway will use the Dockerfile in this directory

4. **Configure Environment Variables**
   - In the Langfuse service, go to "Variables"
   - Add the following required variables:

   ```bash
   # Database (from PostgreSQL service)
   DATABASE_URL=postgresql://postgres:password@postgres.railway.internal:5432/railway
   # Or use Railway's generated DATABASE_URL from PostgreSQL service
   
   # Langfuse Configuration
   NEXTAUTH_SECRET=your-secret-key-here-generate-with-openssl-rand-base64-32
   NEXTAUTH_URL=https://your-langfuse-service.railway.app
   SALT=your-salt-here-generate-with-openssl-rand-base64-32
   
   # Optional: Email configuration (for user invites)
   # SMTP_HOST=smtp.gmail.com
   # SMTP_PORT=587
   # SMTP_USER=your-email@gmail.com
   # SMTP_PASSWORD=your-app-password
   # SMTP_FROM=your-email@gmail.com
   ```

5. **Generate Secrets**
   ```bash
   # Generate NEXTAUTH_SECRET
   openssl rand -base64 32
   
   # Generate SALT
   openssl rand -base64 32
   ```

6. **Get Your Langfuse Keys**
   - Once deployed, visit your Langfuse URL
   - Sign up for the first admin account
   - Go to Settings → API Keys
   - Create a new API key
   - Copy the Public Key and Secret Key

7. **Update Your PEP Backend**
   - Add to your `.env` file:
   ```bash
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=your-public-key-from-langfuse
   LANGFUSE_SECRET_KEY=your-secret-key-from-langfuse
   LANGFUSE_HOST=https://your-langfuse-service.railway.app
   ```

## Environment Variables Reference

### Required
- `DATABASE_URL` - PostgreSQL connection string (auto-provided by Railway if using their PostgreSQL service)
- `NEXTAUTH_SECRET` - Secret for NextAuth.js (generate with `openssl rand -base64 32`)
- `NEXTAUTH_URL` - Your Langfuse public URL (Railway will provide this)
- `SALT` - Salt for encryption (generate with `openssl rand -base64 32`)

### Optional
- `SMTP_*` - Email configuration for user invites
- `LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES` - Enable experimental features
- `TELEMETRY_ENABLED` - Enable telemetry (default: true)

## Accessing Your Langfuse Instance

1. Railway will provide a public URL (e.g., `https://langfuse-production.up.railway.app`)
2. Visit the URL and sign up for the first admin account
3. This account will have full admin privileges

## Connecting Your PEP Backend

After deployment, update your PEP backend `.env`:

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://your-langfuse-service.railway.app
```

Restart your backend service to start sending traces to Langfuse.

## Troubleshooting

- **Database connection issues**: Make sure the PostgreSQL service is running and the DATABASE_URL is correct
- **Can't access Langfuse**: Check that the service is deployed and the public URL is correct
- **No traces appearing**: Verify LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are correct in your backend

## Resources

- [Langfuse Self-Hosting Docs](https://langfuse.com/docs/deployment/self-host)
- [Railway Documentation](https://docs.railway.app)
