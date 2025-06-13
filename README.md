# InfluxDB MCP Server

Model Context Protocol server providing read-only access to InfluxDB v2 for LLMs. Enables querying time-series data via Flux queries and schema discovery.

## Installation

### Standalone using uv + python

```bash
# Clone and install
git clone <repository-url>
cd influxdb-mcp
uv sync

# Run
uv run python -m influxdb_mcp
```

### Using Docker

```bash
# Build and run
docker build -t influxdb-mcp .
docker run -d -p 5001:5001 --env-file .env influxdb-mcp

# Or use docker-compose
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| **InfluxDB Settings** | | | |
| `INFLUXDB_TOKEN` | Auth token | - | **Yes** |
| `INFLUXDB_ORG` | Organization | - | **Yes** |
| `INFLUXDB_HOST` | InfluxDB hostname | `localhost` | No |
| `INFLUXDB_PORT` | InfluxDB port | `8086` | No |
| `INFLUXDB_USE_SSL` | Use HTTPS | `false` | No |
| `INFLUXDB_VERIFY_SSL` | Verify SSL certs | `true` | No |
| `INFLUXDB_TIMEOUT` | Request timeout (ms) | `10000` | No |
| **MCP Settings** | | | |
| `MCP_LISTEN_HOST` | Server bind address | `127.0.0.1` | No |
| `MCP_LISTEN_PORT` | Server port | `5001` | No |
| `MCP_TRANSPORT` | Transport protocol | `streamable-http` | No |

### .env Example

```env
# InfluxDB Configuration
INFLUXDB_HOST=influxdb.example.com
INFLUXDB_PORT=8086
INFLUXDB_TOKEN=your-token-here
INFLUXDB_ORG=your-org

# MCP Configuration
MCP_LISTEN_HOST=0.0.0.0
MCP_LISTEN_PORT=8000
```

## Available Tools

- `test_connection` - Test InfluxDB connection and return status
- `list_buckets` - List all available buckets
- `list_measurements(bucket)` - List measurements in a bucket
- `execute_flux_query(query)` - Execute custom Flux queries

## Available Resources

- `influxdb://buckets` - Live bucket list with metadata
- `influxdb://measurements/{bucket}` - Live measurements for bucket
- `influxdb://status` - Current connection status
- `flux://templates/daily-hourly-average/{bucket}/{measurement}/{field}` - Hourly averages
- `flux://templates/recent-data/{bucket}/{measurement}/{field}/{duration}` - Recent data
- `flux://templates/threshold-alerts/{bucket}/{measurement}/{field}/{threshold}` - Threshold monitoring
- `flux://templates/correlation/{bucket}/{measurement1}/{field1}/{measurement2}/{field2}` - Correlation analysis

Server runs on `http://127.0.0.1:5001/mcp/` by default.

## Author

Developed by [Michael Ludvig](https://github.com/mludvig) and his AI assistants.