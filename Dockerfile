# Use Python 3.11 slim image as base
FROM python:3.11-slim as base

# Install uv (fast Python package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    LOG_DIR=/app/logs \
    ENVIRONMENT=production

# ============================================================================
# Builder stage - Install dependencies
# ============================================================================
FROM base as builder

# Install git - Required because sgtk (ShotGrid Toolkit) and potentially other
# dependencies are installed directly from git repositories
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies (without installing the project itself)
RUN uv sync --frozen --no-install-project --no-dev

# ============================================================================
# Final stage - Minimal runtime image
# ============================================================================
FROM base

# Copy virtual environment from builder stage
# This keeps the final image smaller by not including git and build tools
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY main.py payload_processor.py ./

# Create log directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 9222

# Use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Run uvicorn (without --reload for production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9222"]
