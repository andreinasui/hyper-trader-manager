# HyperTrader Web Dockerfile
# Multi-stage build with Node.js 22.12 and pnpm

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

# Build the application
RUN pnpm build

# ============================================
# Runtime stage
# ============================================
FROM node:22.12.0-alpine AS runner

WORKDIR /app

# Install pnpm for runtime
RUN npm install -g pnpm@10.11.0

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 hypertrader

# Copy built application from builder
COPY --from=builder --chown=hypertrader:nodejs /app/.output ./.output
COPY --from=builder --chown=hypertrader:nodejs /app/package.json ./

# Environment
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000

# Expose port
EXPOSE 3000

# Switch to non-root user
USER hypertrader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start the application
CMD ["node", ".output/server/index.mjs"]
