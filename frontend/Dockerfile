# ─── Stage 1: Build ───────────────────────────────────────────────────────────
FROM node:20 AS builder

WORKDIR /app

# Install dependencies first (layer-cache friendly)
COPY package.json package-lock.json ./
# The lockfile was generated on macOS (darwin-arm64) and only contains
# @rolldown/binding-darwin-arm64. Remove it so npm re-resolves the correct
# linux-x64-gnu native binary for rolldown (used internally by vite 8+).
RUN rm -f package-lock.json && npm install

# Copy source and build
COPY . .

# VITE_API_BASE_URL must be provided at build time via --build-arg
# Example: docker build --build-arg VITE_API_BASE_URL=http://192.168.1.100:8080 .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Fail fast if the URL was not provided
RUN test -n "$VITE_API_BASE_URL" || (echo "ERROR: VITE_API_BASE_URL build-arg is required" && exit 1)

RUN npm run build

# ─── Stage 2: Serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config: enable client-side routing + listen on 5173
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
