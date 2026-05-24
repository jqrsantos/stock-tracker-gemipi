FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.11-slim

# Install curl and Antigravity CLI (agy)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://antigravity.google/cli/install.sh | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

# Copy ONLY the pyproject.toml for this service
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY . .
CMD ["python", "main.py"]
