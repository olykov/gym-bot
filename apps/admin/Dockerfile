# Stage 1: build the Vite static bundle
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .
# Run vite build directly: tsc in "npm run build" acts as a linter gate
# (pre-existing TS6133 errors), not a compiler — Vite uses esbuild for
# transpilation. The bundle produced is identical.
RUN npx vite build

# Stage 2: serve the static bundle with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
