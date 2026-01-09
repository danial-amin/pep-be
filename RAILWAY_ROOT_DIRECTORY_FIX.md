# ⚠️ CRITICAL: Railway Root Directory Configuration

## The Problem

Railway is building from the **root directory** instead of the `backend/` directory. This causes errors like:
- `"/alembic": not found`
- `"/app/requirements.txt": not found`

## The Solution

You **MUST** set the Root Directory in Railway's dashboard. This cannot be done via code - it's a Railway dashboard setting.

## Step-by-Step Fix

### For Backend Service:

1. **Go to Railway Dashboard**
   - Open [railway.app](https://railway.app)
   - Navigate to your project
   - Click on your **backend service**

2. **Open Settings**
   - Click **Settings** tab (or gear icon)
   - Click **Source** section

3. **Set Root Directory**
   - Find **Root Directory** field
   - Enter: `backend` (exactly this, no trailing slash)
   - **SAVE** the settings

4. **Redeploy**
   - Go to **Deployments** tab
   - Click **Redeploy** or trigger a new deployment
   - OR delete the service and recreate it with Root Directory set from the start

### If Settings Don't Apply:

If changing the Root Directory doesn't work, you may need to:

1. **Delete the service** (this won't delete your database)
2. **Create a new service** from the same GitHub repo
3. **IMMEDIATELY set Root Directory to `backend`** before Railway tries to build
4. **Then** add your environment variables
5. **Then** trigger the first deployment

## Verification

After setting Root Directory to `backend`, Railway should:
- ✅ Find `backend/Dockerfile`
- ✅ Find `backend/app/requirements.txt`
- ✅ Find `backend/alembic/` directory
- ✅ Build successfully

## Why This Happens

Railway auto-detects Dockerfiles. When it finds a Dockerfile, it uses that directory as the build context. Since we moved everything to `backend/`, Railway needs to be told to look there.

The `railway.toml` file in `backend/` helps, but Railway still needs the Root Directory setting in the dashboard to know WHERE to look for that `railway.toml` file.

## Quick Checklist

- [ ] Backend service Root Directory = `backend`
- [ ] Frontend service Root Directory = `frontend`  
- [ ] Settings saved
- [ ] New deployment triggered
- [ ] Build succeeds
