# Using Langfuse for Multiple Projects

Langfuse is designed to support multiple projects in a single instance. This guide explains how to set up and manage multiple projects.

## Overview

You can use one Langfuse instance (self-hosted or cloud) for:
- ✅ Multiple different applications
- ✅ Different environments (production, staging, dev)
- ✅ Different teams or clients
- ✅ Different LLM projects

Each project is completely isolated with its own:
- API keys
- Traces and data
- Settings and configuration
- Cost tracking

## Setting Up Multiple Projects

### Step 1: Create Projects in Langfuse

1. **Access Langfuse Dashboard**
   - Go to your Langfuse URL (e.g., `https://your-langfuse.railway.app`)
   - Log in with your admin account

2. **Create New Projects**
   - Click on **"Projects"** in the sidebar
   - Click **"New Project"** button
   - Enter project name (e.g., "PEP - Persona Generator")
   - Click **"Create"**

3. **Repeat for Each Project**
   - Create a project for each application/service
   - Examples:
     - "PEP - Persona Generator"
     - "Customer Support Chatbot"
     - "Document Analysis API"
     - "Content Generation Service"

### Step 2: Generate API Keys for Each Project

1. **Select a Project**
   - Go to the project you want to configure
   - Navigate to **Settings** → **API Keys**

2. **Create API Key**
   - Click **"Create API Key"**
   - Give it a descriptive name:
     - "PEP Backend - Production"
     - "Chatbot API - Staging"
     - etc.
   - Copy both:
     - **Public Key** (starts with `pk-lf-`)
     - **Secret Key** (starts with `sk-lf-`)

3. **Repeat for Each Project**
   - Each project needs its own API keys
   - You can create multiple keys per project (for different environments)

### Step 3: Configure Each Application

#### For PEP Backend

Add to your `.env` file:

```bash
# Langfuse Configuration for PEP Project
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...  # From PEP project
LANGFUSE_SECRET_KEY=sk-lf-...  # From PEP project
LANGFUSE_HOST=https://your-langfuse.railway.app
```

#### For Your Other LLM Project

Add to that project's `.env` file:

```bash
# Langfuse Configuration for Other Project
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...  # From other project
LANGFUSE_SECRET_KEY=sk-lf-...  # From other project
LANGFUSE_HOST=https://your-langfuse.railway.app  # Same instance!
```

**Important**: Use the same `LANGFUSE_HOST` but different API keys for each project.

## Project Organization Best Practices

### 1. Naming Convention

Use clear, descriptive project names:

**Good Examples:**
- `PEP - Persona Generator`
- `Customer Support Chatbot`
- `Document Analysis API`
- `Content Generation Service`

**Avoid:**
- `Project 1`, `Project 2`
- `Test`, `Test2`
- Generic names

### 2. Environment Separation

For the same application in different environments:

**Option A: Separate Projects**
- `PEP - Production`
- `PEP - Staging`
- `PEP - Development`

**Option B: Same Project, Different API Keys**
- One project: `PEP - Persona Generator`
- Multiple keys: `PEP - Prod`, `PEP - Staging`, `PEP - Dev`

### 3. API Key Management

- **Name keys descriptively**: Include project and environment
- **Rotate keys periodically**: For security
- **Use separate keys per environment**: Easier to revoke if needed
- **Document key usage**: Keep track of which key is used where

### 4. Team Access

- Invite team members to specific projects
- Control access per project
- Each team member only sees their assigned projects

## Example: Multi-Project Setup

### Scenario

You have:
1. **PEP Backend** - Persona generation service
2. **Chatbot API** - Customer support chatbot
3. **Document Service** - Document analysis API

### Setup

```
Langfuse Instance (Railway)
│
├── Project: PEP - Persona Generator
│   ├── API Key: pk-lf-pep-prod / sk-lf-pep-prod
│   │   └── Used by: PEP Backend (Production)
│   ├── API Key: pk-lf-pep-staging / sk-lf-pep-staging
│   │   └── Used by: PEP Backend (Staging)
│   └── Traces: All persona generation calls
│
├── Project: Customer Support Chatbot
│   ├── API Key: pk-lf-chatbot / sk-lf-chatbot
│   │   └── Used by: Chatbot API
│   └── Traces: All chatbot interactions
│
└── Project: Document Analysis Service
    ├── API Key: pk-lf-docs / sk-lf-docs
    │   └── Used by: Document Service
    └── Traces: All document processing calls
```

### Configuration Files

**PEP Backend `.env`:**
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-pep-prod
LANGFUSE_SECRET_KEY=sk-lf-pep-prod
LANGFUSE_HOST=https://your-langfuse.railway.app
```

**Chatbot API `.env`:**
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-chatbot
LANGFUSE_SECRET_KEY=sk-lf-chatbot
LANGFUSE_HOST=https://your-langfuse.railway.app
```

**Document Service `.env`:**
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-docs
LANGFUSE_SECRET_KEY=sk-lf-docs
LANGFUSE_HOST=https://your-langfuse.railway.app
```

## Benefits of Multi-Project Setup

### 1. Centralized Observability
- One dashboard for all your LLM applications
- Easy to switch between projects
- Unified view of all LLM usage

### 2. Cost Efficiency
- One Langfuse instance for all projects
- Shared infrastructure costs
- Better resource utilization

### 3. Easy Comparison
- Compare performance across projects
- See which projects use more tokens
- Identify optimization opportunities

### 4. Unified Monitoring
- Set up alerts for all projects
- Monitor overall LLM usage
- Track costs across all projects

### 5. Project Isolation
- Each project's data is separate
- Secure access control
- No data leakage between projects

## Viewing and Filtering Traces

### In Langfuse Dashboard

1. **Switch Between Projects**
   - Use the project dropdown in the top bar
   - Each project shows only its traces

2. **Filter Traces**
   - Filter by model, time range, status
   - Search for specific traces
   - Export data per project

3. **Compare Projects**
   - View metrics across projects
   - Compare token usage
   - Analyze error rates

### Using API

You can also filter by project programmatically:

```python
from langfuse import Langfuse

# Initialize with project-specific keys
langfuse = Langfuse(
    public_key="pk-lf-pep-prod",
    secret_key="sk-lf-pep-prod",
    host="https://your-langfuse.railway.app"
)

# All traces will automatically be associated with the project
# that owns these API keys
```

## Migration: Moving to Multi-Project

If you already have traces in one project:

1. **Keep existing project** for historical data
2. **Create new projects** for new applications
3. **Use new API keys** for new projects
4. **Old traces remain** in the original project

## Troubleshooting

### Traces Appearing in Wrong Project

- **Check API keys**: Make sure you're using the correct keys for each project
- **Verify configuration**: Check `.env` files in each application
- **Restart services**: After changing API keys, restart your applications

### Can't See Traces

- **Check project selection**: Make sure you're viewing the correct project
- **Verify API keys**: Ensure keys are active and correct
- **Check network**: Verify `LANGFUSE_HOST` is correct

### Multiple Projects Using Same Keys

- **Don't do this**: Each project should have unique keys
- **Create new keys**: Generate separate keys for each project
- **Update configuration**: Update each application's `.env`

## Security Considerations

1. **Separate Keys**: Never share API keys between projects
2. **Key Rotation**: Rotate keys periodically
3. **Access Control**: Limit team member access to relevant projects
4. **Environment Variables**: Store keys securely (never commit to git)

## Summary

✅ **One Langfuse instance** can handle multiple projects  
✅ **Each project** has its own API keys  
✅ **Complete isolation** between projects  
✅ **Easy to manage** from one dashboard  
✅ **Cost efficient** - one instance for all projects  

This makes Langfuse perfect for organizations with multiple LLM applications!
