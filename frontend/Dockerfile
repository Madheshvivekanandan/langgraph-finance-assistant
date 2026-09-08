# syntax=docker/dockerfile:1
# check=error=true
# Dev image: runs the Vite dev server with HMR. Tag-pinned only — local dev, not deployed.
FROM node:22-slim

USER node
WORKDIR /app

COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

COPY --chown=node:node . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
