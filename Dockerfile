FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

# uv drives the install from the committed lockfile.
RUN pip install --no-cache-dir uv

# Copy dependency manifests first so the layer caches across code-only changes.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# Now the source.
COPY . .
RUN chmod +x entrypoint.sh

# MCP gateway HTTP transport (streamable HTTP at /mcp).
EXPOSE 8100
ENTRYPOINT ["./entrypoint.sh"]
