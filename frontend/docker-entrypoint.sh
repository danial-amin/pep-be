#!/bin/sh
# Docker entrypoint script to inject runtime configuration

echo "========================================="
echo "Frontend Runtime Configuration"
echo "========================================="

# Get API URL from environment variable (Railway provides this)
API_URL="${VITE_API_URL:-http://localhost:8080/api/v1}"

echo "VITE_API_URL environment variable: ${VITE_API_URL:-<not set, using default>}"
echo "Using API URL: ${API_URL}"
echo ""

# Create config.js with the API URL
echo "Creating config.js with API URL..."
cat > /usr/share/nginx/html/config.js <<EOF
// Runtime configuration injected at container startup
window.APP_CONFIG = {
  VITE_API_URL: '${API_URL}'
};
EOF

echo "Configuration file created successfully"
echo "Config file contents:"
cat /usr/share/nginx/html/config.js
echo ""
echo "========================================="
echo "Starting nginx..."
echo "========================================="

# Start nginx
exec nginx -g "daemon off;"
