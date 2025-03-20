# MCP Server for Managing Coding Preferences

This demonstrates a structured approach for using an [MCP](https://modelcontextprotocol.io/introduction) server to manage coding preferences efficiently. The server can be used with Cursor and provides essential tools for storing, retrieving, and searching coding preferences.

The server supports multiple backend options:
1. [mem0](https://mem0.ai) - Cloud-based memory storage (requires API key)
2. MySQL/MariaDB - Self-hosted relational database (no API key required)

## Installation

1. Clone this repository
2. Initialize the `uv` environment:

```bash
uv venv
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install the dependencies using `uv`:

```bash
# Install in editable mode from pyproject.toml
uv pip install -e .
```

5. Configure your backend:

### For mem0 backend:
Update `.env` file in the root directory with your mem0 API key:

```bash
BACKEND_TYPE=mem0
MEM0_API_KEY=your_api_key_here
```

### For MySQL backend:
Update `.env` file to use MySQL (no API key required):

```bash
BACKEND_TYPE=mysql
MYSQL_URL=mysql+pymysql://root:password@localhost:3306/mem0_mcp  # Adjust as needed
```

## Usage

### Running with Local Python

1. If using MySQL backend, make sure MySQL is running:

```bash
# Install MySQL (Ubuntu/Debian)
sudo apt-get install mysql-server

# Start MySQL
sudo systemctl start mysql

# Create database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS mem0_mcp;"
```

2. Start the MCP server:

```bash
# With default backend (from .env file)
uv run main.py

# Or specify backend directly
BACKEND_TYPE=mysql uv run main.py
```

3. In Cursor, connect to the SSE endpoint, follow this [doc](https://docs.cursor.com/context/model-context-protocol) for reference:

```
http://0.0.0.0:8080/sse
```

4. Open the Composer in Cursor and switch to `Agent` mode.

### Running with Docker

1. Build and run using Docker Compose:

```bash
# Start both the MCP server and MySQL
docker-compose up -d
```

2. In Cursor, connect to the SSE endpoint:

```
http://0.0.0.0:8080/sse
```

3. Open the Composer in Cursor and switch to `Agent` mode.

## Demo with Cursor

https://github.com/user-attachments/assets/56670550-fb11-4850-9905-692d3496231c

## Features

The server provides three main tools for managing code preferences:

1. `add_coding_preference`: Store code snippets, implementation details, and coding patterns with comprehensive context including:
   - Complete code with dependencies
   - Language/framework versions
   - Setup instructions
   - Documentation and comments
   - Example usage
   - Best practices

2. `get_all_coding_preferences`: Retrieve all stored coding preferences to analyze patterns, review implementations, and ensure no relevant information is missed.

3. `search_coding_preferences`: Semantically search through stored coding preferences to find relevant:
   - Code implementations
   - Programming solutions
   - Best practices
   - Setup guides
   - Technical documentation

## Why?

This implementation allows for a persistent coding preferences system that can be accessed via MCP. The SSE-based server can run as a process that agents connect to, use, and disconnect from whenever needed. This pattern fits well with "cloud-native" use cases where the server and clients can be decoupled processes on different nodes.

### Server

By default, the server runs on 0.0.0.0:8080 but is configurable with command line arguments like:

```
uv run main.py --host <your host> --port <your port>
```

The server exposes an SSE endpoint at `/sse` that MCP clients can connect to for accessing the coding preferences management tools.

### Deploying to Kubernetes

The repository includes Kubernetes deployment files in the `kubernetes/` directory.

1. Build and push the Docker image to your registry:

```bash
# Build the image
docker build -t your-registry/mem0-mcp:latest .

# Push to your registry
docker push your-registry/mem0-mcp:latest
```

2. Update the image reference in `kubernetes/mem0-mcp-deployment.yaml`:

```yaml
image: your-registry/mem0-mcp:latest
```

3. Create a namespace and deploy:

```bash
# Create namespace
kubectl create namespace mem0-mcp

# Apply the Kubernetes manifests
kubectl apply -k kubernetes/
```

4. Access the service:

```bash
# Port forward for local access
kubectl -n mem0-mcp port-forward svc/mem0-mcp 8080:8080
```

5. In Cursor, connect to the SSE endpoint:

```
http://localhost:8080/sse
```

The Kubernetes deployment includes:
- MySQL database with persistent storage
- mem0-mcp server configured to use MySQL backend
- Ingress for external access (requires configuration)

