# ADHD_MCP server image (ADR 0013). Built in CI as a check; not published to a registry.
# Synthetic sample data is included at /app/sample-data. The server never needs write access.
#
#   docker build -t adhd-mcp .
#   docker run --rm -i -e ADHD_MCP_FIXTURE_DIR=/app/sample-data adhd-mcp
#
# Keep the uv version equal to the one in .github/workflows/ci.yml (a test checks it).
FROM ghcr.io/astral-sh/uv:0.11.32 AS uv

FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 adhd
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY tests/personas/bundles /app/sample-data
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER adhd
ENTRYPOINT ["adhd-mcp"]
