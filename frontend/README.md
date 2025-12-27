# PEP Frontend

React frontend for the PEP Persona Generator application.

## Features

- 📄 Document upload and management (Context & Interview documents)
- 👥 Persona generation and expansion
- 🎨 AI-generated persona images
- 💬 Prompt completion using document context
- 🎨 Modern UI with Tailwind CSS

## Development

### Prerequisites

- Node.js 20+
- npm or yarn

### Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file (or copy from `.env.example`):
```bash
VITE_API_URL=http://localhost:8080/api/v1
```

3. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Production Build

### Using Docker

```bash
# Build the image
docker build -t pep-frontend --build-arg VITE_API_URL=http://your-api-url/api/v1 .

# Run the container
docker run -p 3000:80 pep-frontend
```

### Local Build

```bash
npm run build
npm run preview
```

## Docker Compose

The frontend is included in the main `docker-compose.yml` file. To run all services:

```bash
docker-compose up -d
```

The frontend will be available at `http://localhost:3000`

## Environment Variables

- `VITE_API_URL`: Backend API URL (default: `http://localhost:8080/api/v1`)

Note: Vite requires environment variables to be prefixed with `VITE_` to be exposed to the client.

