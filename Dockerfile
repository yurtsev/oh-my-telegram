FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project


FROM python:3.12-slim-bookworm AS runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -d /app -s /usr/sbin/nologin app

COPY --from=builder /app/.venv /app/.venv
# config.toml монтируется Compose read-only, в образ его не запекаем.
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN chown -R app:app /app
USER app

CMD ["sh", "-c", "alembic upgrade head && python -m src.runtime.app"]
