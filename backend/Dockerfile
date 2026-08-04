FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app
COPY pyproject.toml uv.lock alembic.ini ./
RUN uv sync --frozen --no-dev && uv cache clean
COPY app/ app/
COPY alembic/ alembic/
COPY scripts/ scripts/
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
