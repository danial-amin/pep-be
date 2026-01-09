#!/bin/sh
# Docker entrypoint script to inject runtime configuration

echo "========================================="
echo "Frontend Runtime Configuration"
echo "========================================="

# Get API URL from environment variable (Railway provides this)
# Remove trailing slashes to ensure consistent URL format
RAW_API_URL="${VITE_API_URL:-http://localhost:8080/api/v1}"
API_URL=$(echo "$RAW_API_URL" | sed 's:/*$::')

echo "VITE_API_URL environment variable: ${VITE_API_URL:-<not set, using default>}"
echo "Using API URL: ${API_URL}"
echo ""

# Verify nginx html directory exists
if [ ! -d "/usr/share/nginx/html" ]; then
    echo "ERROR: /usr/share/nginx/html directory does not exist!"
    ls -la /usr/share/nginx/ || true
    exit 1
fi

# List files in html directory for debugging
echo "Files in /usr/share/nginx/html:"
ls -la /usr/share/nginx/html/ | head -10
echo ""

# Create config.js with the API URL
echo "Creating config.js with API URL..."
cat > /usr/share/nginx/html/config.js <<EOF
// Runtime configuration injected at container startup
window.APP_CONFIG = {
  VITE_API_URL: '${API_URL}'
};
EOF

# Verify config.js was created
if [ ! -f "/usr/share/nginx/html/config.js" ]; then
    echo "ERROR: Failed to create config.js!"
    exit 1
fi

echo "Configuration file created successfully"
echo "Config file contents:"
cat /usr/share/nginx/html/config.js
echo ""

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "ERROR: nginx configuration test failed!"
    exit 1
fi

echo "========================================="
echo "Starting nginx..."
echo "========================================="

# Start nginx in foreground (this will block and keep container running)
# Nginx will handle requests immediately when it starts
exec nginx -g "daemon off;"
