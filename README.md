# InfluxDB MCP Server

A FastMCP server providing read-only access to InfluxDB v2 databases. This server enables Large Language Models (LLMs) to query and analyze time-series data stored in InfluxDB through the Model Context Protocol (MCP).

## Features

- **Read-only operations** for security
- **FastMCP framework** for high performance
- **Comprehensive querying** capabilities via custom Flux queries
- **Schema discovery** (buckets and measurements)
- **Custom Flux queries** support
- **Environment-based configuration** via `.env` file
- **uvx support** for easy installation and deployment

## Prerequisites

- Python 3.12+
- uv package manager (automatically installed if using uvx)
- Access to an InfluxDB v2 instance
- Valid InfluxDB authentication token

## Installation

### Using uvx (Recommended)

```bash
# Install and run directly from source
uvx --from git+https://github.com/your-repo/influxdb-mcp influxdb-mcp

# Or install for persistent use
uvx install influxdb-mcp
```

### Using Docker (Recommended for Production)

```bash
# Build the Docker image
docker build -t influxdb-mcp .

# Run with environment variables
docker run -d \
  --name influxdb-mcp \
  -p 8000:8000 \
  -e INFLUXDB_HOST=your-influxdb-host \
  -e INFLUXDB_TOKEN=your-token \
  -e INFLUXDB_ORG=your-org \
  influxdb-mcp

# Or use docker-compose
docker-compose up -d

# To include a local InfluxDB instance for testing
docker-compose --profile with-influxdb up -d
```

### Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd influxdb-mcp

# Install dependencies
uv sync

# Run the server
uv run influxdb-mcp
```

## Configuration

Create a `.env` file in the project root with your InfluxDB connection details:

```bash
# Copy the example configuration
cp .env.example .env
```

Edit `.env` with your InfluxDB settings:

```env
# InfluxDB connection settings
INFLUXDB_HOST=localhost
INFLUXDB_PORT=8086
INFLUXDB_TOKEN=your-influxdb-token-here
INFLUXDB_ORG=your-organization-name

# Optional settings
INFLUXDB_USE_SSL=false
INFLUXDB_VERIFY_SSL=true
INFLUXDB_TIMEOUT=10000
```

### Configuration Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `INFLUXDB_HOST` | InfluxDB server hostname | `localhost` | No |
| `INFLUXDB_PORT` | InfluxDB server port | `8086` | No |
| `INFLUXDB_TOKEN` | Authentication token | - | **Yes** |
| `INFLUXDB_ORG` | Organization name | - | **Yes** |
| `INFLUXDB_USE_SSL` | Use HTTPS connection | `false` | No |
| `INFLUXDB_VERIFY_SSL` | Verify SSL certificates | `true` | No |
| `INFLUXDB_TIMEOUT` | Request timeout (ms) | `10000` | No |

## Usage

### Running the Server

```bash
# Using uv
uv run influxdb-mcp

# Using uvx
uvx influxdb-mcp

# Using Docker
docker run -d \
  --name influxdb-mcp \
  -p 8000:8000 \
  --env-file .env \
  influxdb-mcp

# Using docker-compose
docker-compose up -d

# Direct Python execution
python -m influxdb_mcp
```

The server will start on `http://127.0.0.1:8000` by default, with the MCP endpoint available at `http://127.0.0.1:8000/mcp/`.

#### Health Check

A dedicated health check endpoint is available at `http://127.0.0.1:8000/healthcheck` for monitoring and Docker health checks. This endpoint returns:

```json
{
  "status": "healthy",
  "service": "influxdb-mcp",
  "influxdb_status": "connected"
}
```

The endpoint will return HTTP 200 for healthy status or HTTP 503 for unhealthy status.

### Available Tools

The server provides the following MCP tools:

#### 1. `test_connection`
Test the connection to InfluxDB and return status information.

```json
{
  "name": "test_connection"
}
```

#### 2. `list_buckets`
List all buckets available in the InfluxDB organization.

```json
{
  "name": "list_buckets"
}
```

#### 3. `list_measurements`
List all available measurements in a specific bucket.

```json
{
  "name": "list_measurements",
  "arguments": {
    "bucket": "my-bucket"
  }
}
```

#### 4. `execute_flux_query`
Execute a custom Flux query against the InfluxDB database.

```json
{
  "name": "execute_flux_query",
  "arguments": {
    "query": "from(bucket: \"my-bucket\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"temperature\")"
  }
}
```

#### 5. `get_server_info`
Get information about the MCP server and its configuration.

```json
{
  "name": "get_server_info"
}
```

### Available Resources

The server provides sample Flux query templates as MCP resources. These are ready-to-use query templates for common time-series analysis patterns:

#### 1. `flux://queries/daily-hourly-average`
**Daily Hourly Average Query** - Retrieves the last 1 day of a measurement with hourly averages.

#### 2. `flux://queries/weekly-daily-summary`
**Weekly Daily Summary Query** - Retrieves the last 7 days of data with daily summaries (min, max, mean).

#### 3. `flux://queries/anomaly-detection`
**Anomaly Detection Query** - Detects anomalies using statistical outliers (values beyond 2 standard deviations).

#### 4. `flux://queries/top-n-values`
**Top N Values Query** - Finds the top N highest values in a time range.

#### 5. `flux://queries/rate-of-change`
**Rate of Change Query** - Calculates the rate of change between consecutive measurements.

#### 6. `flux://queries/moving-average`
**Moving Average Query** - Calculates a moving average over a specified window.

#### 7. `flux://queries/downsampling`
**Data Downsampling Query** - Downsamples high-frequency data to lower frequency with aggregation.

#### 8. `flux://queries/correlation-analysis`
**Correlation Analysis Query** - Analyzes correlation between two measurements.

#### 9. `flux://queries/threshold-monitoring`
**Threshold Monitoring Query** - Monitors values that cross specified thresholds.

### Example Queries

#### Get system metrics for the last hour
```flux
from(bucket: "system")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage_percent")
  |> aggregateWindow(every: 5m, fn: mean)
```

#### Find temperature anomalies
```flux
from(bucket: "sensors")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "temperature")
  |> filter(fn: (r) => r._value > 80.0 or r._value < 10.0)
```

## Development

### Project Structure

```
influxdb-mcp/
├── src/
│   └── influxdb_mcp/
│       ├── __init__.py          # Package initialization
│       ├── server.py            # FastMCP server implementation
│       ├── config.py            # Configuration management
│       └── influxdb_client.py   # InfluxDB client wrapper
├── .env.example                 # Example environment configuration
├── .vscode/
│   └── mcp.json                # VS Code MCP server configuration
├── pyproject.toml              # Project dependencies and metadata
├── README.md                   # This file
└── uv.lock                     # Dependency lock file
```

### Running Tests

```bash
# Install test dependencies
uv sync --dev

# Run tests (when implemented)
uv run pytest
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run mypy src/
```

## VS Code Integration

The project includes VS Code MCP server configuration in `.vscode/mcp.json`. This allows you to debug the MCP server directly in VS Code using HTTP transport.

To debug:
1. Open the project in VS Code
2. Run the task "Run InfluxDB MCP Server (HTTP)" to start the server
3. The MCP server configuration will be automatically detected at `http://127.0.0.1:8000/mcp`
4. Use the MCP debugging features in VS Code to test the server

### Client Connection

To connect to the HTTP server from a FastMCP client:

```python
from fastmcp import Client
import asyncio

async def main():
    async with Client("http://127.0.0.1:8000/mcp") as client:
        # Test connection
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        # Test a tool
        result = await client.call_tool("test_connection")
        print(f"Connection test: {result}")

asyncio.run(main())
```

## Security Considerations

- **Read-only access**: The server only supports read operations for security
- **Token-based authentication**: Uses InfluxDB's built-in token authentication
- **SSL/TLS support**: Configurable SSL connections for secure communication
- **Environment variables**: Sensitive configuration stored in environment variables

## Troubleshooting

### Connection Issues

1. **Verify InfluxDB is running**: Check that your InfluxDB instance is accessible
2. **Check credentials**: Ensure your token, organization, and bucket are correct
3. **Network connectivity**: Verify firewall rules and network connectivity
4. **SSL configuration**: If using SSL, ensure certificates are valid

### Common Errors

- **"InfluxDB token cannot be empty"**: Set the `INFLUXDB_TOKEN` environment variable
- **"Connection failed"**: Check host, port, and network connectivity
- **"Organization not found"**: Verify the organization name is correct
- **"Bucket not found"**: Ensure the bucket exists and is accessible

### Debug Mode

Enable debug logging by setting the log level:

```bash
# Native installation
export LOG_LEVEL=DEBUG
uv run influxdb-mcp

# Docker
docker run -e LOG_LEVEL=DEBUG influxdb-mcp

# Docker Compose
LOG_LEVEL=DEBUG docker-compose up
```

### Docker Troubleshooting

**Container Health Check**: Check if the container is healthy:
```bash
docker ps
docker logs influxdb-mcp
```

**Network Issues**: If running InfluxDB in another container:
```bash
# Use container name or service name as host
docker run -e INFLUXDB_HOST=influxdb influxdb-mcp
```

**Volume Mounting**: For persistent configuration:
```bash
docker run -v $(pwd)/.env:/app/.env:ro influxdb-mcp
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and ensure all tests pass
6. Submit a pull request

## License

[MIT License](LICENSE)

## Related Projects

- [FastMCP](https://github.com/jlowin/fastmcp) - High-performance MCP framework
- [InfluxDB](https://github.com/influxdata/influxdb) - Time series database
- [Model Context Protocol](https://github.com/modelcontextprotocol) - MCP specification

## Support

For support and questions:

- **Issues**: Open an issue on GitHub
- **Documentation**: See the [FastMCP documentation](https://fastmcp.com)
- **InfluxDB**: See the [InfluxDB documentation](https://docs.influxdata.com)