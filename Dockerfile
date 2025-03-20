FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install uv
RUN pip install --no-cache-dir uv

# Create and activate virtual environment, install dependencies
RUN uv venv .venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Expose the default port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["/app/.venv/bin/python", "main.py"]