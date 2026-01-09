#!/bin/sh
# Docker entrypoint script to inject runtime configuration
set -e

# Get API URL from environment variable (Railway provides this)
# Remove trailing slashes to ensure consistent URL format
RAW_API_URL="${VITE_API_URL:-http://localhost:8080/api/v1}"
API_URL=$(echo "$RAW_API_URL" | sed 's:/*$::')

echo "========================================="
echo "Frontend Runtime Configuration"
echo "========================================="
echo "VITE_API_URL: ${VITE_API_URL:-<not set, using default>}"
echo "Using API URL: ${API_URL}"
echo ""

# Verify nginx html directory exists
[ -d "/usr/share/nginx/html" ] || { echo "ERROR: /usr/share/nginx/html directory does not exist!"; exit 1; }

# Create config.js with the API URL
cat > /usr/share/nginx/html/config.js <<EOF
// Runtime configuration injected at container startup
window.APP_CONFIG = {
  VITE_API_URL: '${API_URL}'
};
EOF

# Verify config.js was created
[ -f "/usr/share/nginx/html/config.js" ] || { echo "ERROR: Failed to create config.js!"; exit 1; }

echo "Configuration file created successfully"
echo "Config: $(cat /usr/share/nginx/html/config.js)"
echo ""

# Test nginx configuration (silent unless error)
nginx -t > /dev/null 2>&1 || { echo "ERROR: nginx configuration test failed!"; nginx -t; exit 1; }

echo "Starting nginx..."
echo "========================================="

# Start nginx in foreground (this will block and keep container running)
exec nginx -g "daemon off;"
