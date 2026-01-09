#!/bin/sh
# Docker entrypoint script to inject runtime configuration

# Get API URL from environment variable (Railway provides this)
# Remove trailing slashes to ensure consistent URL format
RAW_API_URL="${VITE_API_URL:-http://localhost:8080/api/v1}"
API_URL=$(echo "$RAW_API_URL" | sed 's:/*$::')

# Create config.js with the API URL (must be fast, no verbose output)
cat > /usr/share/nginx/html/config.js <<EOF
// Runtime configuration injected at container startup
window.APP_CONFIG = {
  VITE_API_URL: '${API_URL}'
};
EOF

# Start nginx immediately (no delays, no tests - just start)
exec nginx -g "daemon off;"
