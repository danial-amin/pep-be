# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build argument for API URL
ARG VITE_API_URL=http://localhost:8080/api/v1
ENV VITE_API_URL=$VITE_API_URL

# Display build-time configuration
RUN echo "=========================================" && \
    echo "Frontend Build Configuration:" && \
    echo "=========================================" && \
    echo "VITE_API_URL (build-time): ${VITE_API_URL}" && \
    echo "========================================="

# Build the application
RUN npm run build

# Generate config.js at build time (not runtime)
# Remove trailing slash from API URL
RUN API_URL=$(echo "${VITE_API_URL}" | sed 's:/*$::') && \
    echo "// Build-time configuration" > /app/dist/config.js && \
    echo "window.APP_CONFIG = {" >> /app/dist/config.js && \
    echo "  VITE_API_URL: '${API_URL}'" >> /app/dist/config.js && \
    echo "};" >> /app/dist/config.js && \
    echo "Generated config.js:" && \
    cat /app/dist/config.js

# Production stage
FROM nginx:alpine

# Copy built files to nginx (includes config.js)
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy startup script
COPY start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh

EXPOSE 80

# Use startup script to handle Railway's PORT variable
CMD ["/start-nginx.sh"]

