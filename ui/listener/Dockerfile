FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.11-slim

# Install Node.js and Gemini CLI
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @google/gemini-cli && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=uv /usr/bin/uv /usr/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml .
RUN uv pip install --system --no-cache -e .

COPY . .
CMD ["python", "main.py"]
