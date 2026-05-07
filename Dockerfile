# Stage 1: install all deps (dev + prod) for build
FROM node:22-slim AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: build
FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: minimal runtime (standalone output only)
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN groupadd --system songa && useradd --system --gid songa songa
COPY --from=builder --chown=songa:songa /app/.next/standalone ./
COPY --from=builder --chown=songa:songa /app/.next/static ./.next/static
COPY --from=builder --chown=songa:songa /app/public ./public
USER songa
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
