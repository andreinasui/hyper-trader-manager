# HyperTrader Web Dockerfile
# Multi-stage build: SolidStart with Node.js runtime

# ============================================
# Build stage
# ============================================
FROM node:22-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm@10

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Set default environment variables (can be overridden by docker-compose env_file)
ENV API_URL=http://api:8000

# Build the SolidStart application
RUN pnpm build

# ============================================
# Runtime stage
# ============================================
FROM node:22-alpine AS runner

WORKDIR /app

# Copy built output from builder
COPY --from=builder /app/.output /app/.output

# Expose port
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ 2>/dev/null || exit 1

# Run the server
CMD ["node", ".output/server/index.mjs"]
