# Use Python 3.11 slim image as base
FROM python:3.11-slim as base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    LOG_DIR=/app/logs

# Install dependencies first (for better caching)
FROM base as builder

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Final stage
FROM base

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY main.py payload_processor.py ./

# Create log directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 9222

# Use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Run uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9222"]
