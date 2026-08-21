FROM node:20-alpine AS install
WORKDIR /workspace
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS compile
WORKDIR /workspace
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=install /workspace/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS web
WORKDIR /srv/app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -S runline && adduser -S -G runline runline
COPY --from=compile --chown=runline:runline /workspace/.next/standalone ./
COPY --from=compile --chown=runline:runline /workspace/.next/static ./.next/static
COPY --from=compile --chown=runline:runline /workspace/public ./public
USER runline
EXPOSE 3000
ENTRYPOINT ["node", "server.js"]
