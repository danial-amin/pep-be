#!/bin/sh
# Start nginx on Railway's PORT or default to 80

PORT=${PORT:-80}

echo "Starting nginx on port ${PORT}..."

# Replace port in nginx config if PORT is not 80
if [ "$PORT" != "80" ]; then
    echo "Updating nginx config to listen on port ${PORT}..."
    sed -i "s/listen 80;/listen ${PORT};/" /etc/nginx/conf.d/default.conf
fi

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t || { echo "ERROR: nginx config test failed!"; exit 1; }

echo "Starting nginx..."
# Start nginx
exec nginx -g "daemon off;"
