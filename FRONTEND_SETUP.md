# Frontend Setup Guide

The frontend is a React + TypeScript application built with Vite and Tailwind CSS.

## Quick Start

### Using Docker Compose (Recommended)

1. Make sure you have a `.env` file in the root directory with:
```env
VITE_API_URL=http://localhost:8080/api/v1
OPENAI_API_KEY=your_key_here
```

2. Start all services:
```bash
docker-compose up -d
```

3. Access the frontend at: `http://localhost:3000`

### Local Development

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file:
```env
VITE_API_URL=http://localhost:8080/api/v1
```

4. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Features

### Documents Page
- Upload context documents (research, reports, background info)
- Upload interview documents (transcripts, user research)
- View and filter processed documents
- Drag and drop file upload support

### Personas Page
- Generate persona sets from processed documents
- Expand basic personas into detailed profiles
- Generate AI images for personas
- View and manage persona sets

### Prompts Page
- Complete prompts using context from documents
- Adjustable token limits
- Real-time prompt completion

## Architecture

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Routing**: React Router

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable components (if needed)
│   ├── pages/          # Page components
│   │   ├── DocumentsPage.tsx
│   │   ├── PersonasPage.tsx
│   │   └── PromptsPage.tsx
│   ├── services/       # API client
│   │   └── api.ts
│   ├── types/          # TypeScript types
│   │   └── index.ts
│   ├── App.tsx         # Main app component with routing
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── Dockerfile          # Production build
├── Dockerfile.dev      # Development build
├── nginx.conf          # Nginx configuration
└── package.json
```

## Docker

### Production Build
The production Dockerfile uses a multi-stage build:
1. Builds the React app with Vite
2. Serves it with Nginx

### Development Build
For development, you can use `Dockerfile.dev` which runs the Vite dev server with hot reload.

To use development mode in docker-compose, uncomment the development section in `docker-compose.yml`.

## Environment Variables

- `VITE_API_URL`: Backend API URL (required at build time for production)

Note: Vite requires environment variables to be prefixed with `VITE_` to be exposed to the client bundle.

## API Integration

The frontend communicates with the backend API at `/api/v1`:

- `/documents/*` - Document management
- `/personas/*` - Persona generation and management
- `/prompts/*` - Prompt completion

See `src/services/api.ts` for the complete API client implementation.

## Building for Production

```bash
cd frontend
npm run build
```

The built files will be in the `dist/` directory, ready to be served by any static file server.

## Troubleshooting

### CORS Issues
If you encounter CORS errors, make sure:
1. The backend CORS settings allow your frontend origin
2. The `VITE_API_URL` is correctly set
3. Both services are running

### API Connection Issues
- Verify the backend is running on port 8080
- Check that `VITE_API_URL` points to the correct backend URL
- In Docker, use `http://localhost:8080` (not service names) since the browser makes the requests

### Build Issues
- Make sure Node.js 20+ is installed
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check that all environment variables are set correctly

