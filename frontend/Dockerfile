FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build:brolly

FROM ghcr.io/nginx/nginx-unprivileged:stable-alpine
COPY infra/docker/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist-brolly /usr/share/nginx/html/skillforge
EXPOSE 8080
# No template rewriting is needed on the read-only container filesystem.
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
