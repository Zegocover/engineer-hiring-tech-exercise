# syntax=docker/dockerfile:1
# Crawler dashboard image (Next.js standalone output).
#   docker build front-end
# The crawler API address is read at request time from CRAWLER_API_URL, so set it when
# running the container, not when building it.

ARG NODE_VERSION=24

# --- deps: install exactly what package-lock.json pins ---------------------------------
FROM node:${NODE_VERSION}-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# --- build: production build with standalone output ------------------------------------
FROM deps AS build
COPY . .
ENV NEXT_OUTPUT=standalone \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- runtime: the traced server and static assets only, run unprivileged ---------------
FROM node:${NODE_VERSION}-slim
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
# public/ is not copied: the app has no public assets (the favicon lives in src/app).
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --start-interval=1s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"]

CMD ["node", "server.js"]
