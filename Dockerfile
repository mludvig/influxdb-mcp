# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install uv

# Create app directory
WORKDIR /app

# Copy all necessary files for the build
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Create non-root user for security
RUN groupadd appuser && useradd -m -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the default FastMCP HTTP port
EXPOSE 8000

# Health check using the dedicated healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthcheck || exit 1

# Set the default command
CMD ["uv", "run", "python", "-m", "influxdb_mcp"]
