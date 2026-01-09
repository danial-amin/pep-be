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
    echo "Note: Runtime config will override this" && \
    echo "========================================="

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

# Use entrypoint script to inject runtime config and start nginx
# This ensures config.js is created before nginx starts
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD []

