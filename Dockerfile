FROM python:3.13.7-slim AS builder

# Prevent .pyc and force unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install system dependencies in a single layer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update --yes && \
    apt-get upgrade --yes && \
    apt-get install --no-install-recommends --yes \
        # Build dependencies for Python packages
        gcc \
        g++ \
        libc6-dev \
        libffi-dev \
        python3-dev \
        libpq-dev \
        # Runtime dependencies
        postgresql-client \
        curl

# Install uv (cached layer)
RUN pip install --upgrade pip && pip install uv

# Copy dependency metadata first for better layer caching
COPY pyproject.toml uv.lock* ./

# Install project deps using uv pip install directly from pyproject.toml
# Conditionally install dev dependencies based on INSTALL_DEV_DEPS environment variable
# If dev dependencies are defined as optional-dependencies in pyproject.toml, use --extra dev
ARG INSTALL_DEV_DEPS=false
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        uv pip install --system --extra dev .; \
    else \
        uv pip install --system .; \
    fi

# Production stage
FROM python:3.13.7-slim AS production

# Prevent .pyc and force unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install only runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update --yes && \
    apt-get upgrade --yes && \
    apt-get install --no-install-recommends --yes \
        postgresql-client \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-spa

# Copy Python environment from builder
COPY --from=builder /usr/local /usr/local

# Create non-root user
RUN adduser --disabled-password --gecos '' claims

# Create necessary directories with proper permissions
RUN mkdir -p /code/staticfiles /code/media /code/logs

# Copy the application code (this changes frequently, so it's last)
COPY --chown=claims:claims . .

# Ensure the user owns all directories and files
RUN chown -R claims:claims /code

USER claims
