# All base images are pinned by multi-platform manifest digest.
FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS web-build
WORKDIR /build
COPY package.json package-lock.json tsconfig.base.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/design-system/package.json packages/design-system/package.json
RUN npm ci
COPY apps/web apps/web
COPY packages/design-system packages/design-system
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.11.3@sha256:90bbb3c16635e9627f49eec6539f956d70746c409209041800a0280b93152823 AS uv
FROM python:3.14.6-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8 AS api-build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY apps/api/pyproject.toml apps/api/uv.lock ./
# Runtime dependencies only; no project build isolation or unlocked build tools.
RUN uv sync --frozen --no-dev --no-install-project --no-editable --no-cache

FROM python:3.14.6-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8 AS runtime
RUN groupadd --gid 10001 forge && useradd --uid 10001 --gid forge --no-create-home forge
WORKDIR /app/api
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/api/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    WEB_BUILD_DIR=/app/web
COPY --from=api-build /app/.venv /app/.venv
COPY apps/api/src ./src
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./alembic.ini
COPY --from=web-build /build/apps/web/dist /app/web
USER 10001:10001
CMD ["python", "-m", "forge_api.serve"]
