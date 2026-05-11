FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.11-slim

# Install uv binary
COPY --from=uv /uv /usr/bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy ONLY the pyproject.toml for this service
COPY pyproject.toml .

# Install dependencies into the system environment
RUN uv pip install --system --no-cache .

# Copy the rest of the app
COPY . .

CMD ["streamlit", "run", "app.py"]
