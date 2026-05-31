FROM node:20-alpine AS deps
WORKDIR /app/apps/frontend
COPY apps/frontend/package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/apps/frontend/node_modules ./apps/frontend/node_modules
COPY apps/frontend ./apps/frontend
WORKDIR /app/apps/frontend
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app/apps/frontend
ENV NODE_ENV=production
COPY --from=builder /app/apps/frontend/package*.json ./
COPY --from=builder /app/apps/frontend/node_modules ./node_modules
COPY --from=builder /app/apps/frontend/.next ./.next
EXPOSE 3000
CMD ["sh", "-c", "npm run start -- --hostname 0.0.0.0 --port ${PORT:-3000}"]
