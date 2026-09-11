# syntax=docker/dockerfile:1.7
# One image, three entrypoints (api, worker, scheduler). Build from the repository root:
#   docker build -f backend/Dockerfile -t mizan-labs/platform .
FROM python:3.12-slim AS build
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
      libharfbuzz0b libffi8 shared-mime-info fonts-dejavu-core fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/README.md ./backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace
COPY backend/ ./backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:$PATH" PORT=8080
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
      libharfbuzz0b libffi8 shared-mime-info fonts-dejavu-core fonts-noto-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=build --chown=app:app /app /app
WORKDIR /app/backend
USER app
EXPOSE 8080
ENTRYPOINT ["/app/backend/entrypoint.sh"]
CMD ["api"]
