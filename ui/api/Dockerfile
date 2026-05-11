FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.11-slim

# Install uv binary
COPY --from=uv /usr/bin/uv /usr/bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml .

# Install dependencies into the system environment
RUN uv pip install --system --no-cache -e .

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
