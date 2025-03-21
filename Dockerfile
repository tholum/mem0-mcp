FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    default-libmysqlclient-dev \
    build-essential \
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
# Default to Redis backend to run without mem0 account
ENV BACKEND_TYPE=redis
# Default Redis URL (override with docker-compose or command line)
ENV REDIS_URL=redis://redis:6379/0
# MySQL URL (when using MySQL backend)
ENV MYSQL_URL=mysql+pymysql://root:password@mysql:3306/mem0_mcp

# Command to run the application
CMD ["/app/.venv/bin/python", "main.py"]