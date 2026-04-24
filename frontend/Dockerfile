# Supports Docker build context = `frontend/` (recommended on Railway) OR repo root.
# If Railway ever sends the whole repo as context without Root Directory, the second branch still finds `frontend/`.
FROM node:20-alpine AS builder

WORKDIR /app

COPY . /src
RUN set -eux; \
    if [ -f /src/package.json ]; then \
      cp -r /src/. .; \
    elif [ -f /src/frontend/package.json ]; then \
      cp -r /src/frontend/. .; \
    else \
      echo "ERROR: Cannot find frontend package.json."; \
      ls -la /src || true; \
      exit 1; \
    fi; \
    rm -rf /src

RUN if [ ! -f package-lock.json ]; then \
      echo "ERROR: package-lock.json missing. Commit lockfile under frontend/."; \
      exit 1; \
    fi

RUN npm ci

ARG VITE_API_URL=http://localhost:8080/api/v1
ENV VITE_API_URL=$VITE_API_URL
ENV NODE_OPTIONS=--max-old-space-size=4096

RUN echo "VITE_API_URL (build-time): ${VITE_API_URL}" && npm run build

RUN API_URL=$(echo "${VITE_API_URL}" | sed 's:/*$::') && \
    echo "// Build-time configuration" > /app/dist/config.js && \
    echo "window.APP_CONFIG = {" >> /app/dist/config.js && \
    echo "  VITE_API_URL: '${API_URL}'" >> /app/dist/config.js && \
    echo "};" >> /app/dist/config.js

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh
EXPOSE 80
CMD ["/start-nginx.sh"]
