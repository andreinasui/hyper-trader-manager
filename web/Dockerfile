# HyperTrader Web Dockerfile
# Multi-stage build: Vite build → nginx static serving

# ============================================
# Build stage
# ============================================
FROM node:22.12.0-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm@10.11.0

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the Vite application (outputs to dist/)
RUN pnpm build

# ============================================
# Runtime stage - serve static files with nginx
# ============================================
FROM nginx:1.27-alpine AS runner

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# nginx runs as root by default; it drops to www-data for workers
CMD ["nginx", "-g", "daemon off;"]
