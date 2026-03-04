# eafw_storymaps — VEDA UI Scrollytelling
# Multi-stage build: install deps → build → slim runtime

# ---- Stage 1: Dependencies ----
FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY eafw_storymaps/package.json ./
RUN yarn install --frozen-lockfile --network-timeout 120000 || yarn install --network-timeout 120000

# ---- Stage 2: Build ----
FROM node:20-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY eafw_storymaps/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN yarn build

# ---- Stage 3: Runtime ----
FROM node:20-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/shims ./shims
COPY --from=builder /app/app/content ./app/content
COPY --from=builder /app/app/lib ./app/lib

EXPOSE 3001
CMD ["node_modules/.bin/next", "start", "-p", "3001"]
