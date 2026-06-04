# Stage 1: build the Vite static bundle
# Build context MUST be the repo root so packages/api-contract/openapi.yaml
# is available at packages/api-contract/openapi.yaml inside the build context.
# The TS client (packages/api-contract/clients/typescript/) is gitignored and
# generated here from the spec using openapi-typescript before vite builds.
FROM node:20-alpine AS build

WORKDIR /app

# Copy the app manifest first for layer-cache efficiency, then install deps.
COPY apps/web/package.json .
RUN npm install

# Generate the TypeScript API client from the contract spec.
# The alias "@api-contract" in vite.config.ts points to
# ../../packages/api-contract/clients/typescript/ (relative to apps/web),
# which resolves to /app/../../packages/api-contract/clients/typescript/ at
# build time — but we're at WORKDIR /app, so we write it there explicitly.
RUN mkdir -p /packages/api-contract/clients/typescript
COPY packages/api-contract/openapi.yaml /packages/api-contract/openapi.yaml
RUN npx --yes openapi-typescript@7 /packages/api-contract/openapi.yaml \
    -o /packages/api-contract/clients/typescript/schema.ts

# Copy the full app source.
COPY apps/web/ .

# Patch the vite alias resolution: __dirname is /app, so ../../packages/api-contract
# resolves to /packages/api-contract — which is where we generated the client above.
# npm run build = tsc (type-check gate) && vite build (esbuild transpile).
RUN npm run build

# Stage 2: serve the static bundle with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
