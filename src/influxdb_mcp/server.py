"""
MCP server providing read-only access to InfluxDB v2 database.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import get_config
from .influxdb_client import InfluxDBManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name="influxdb-mcp",
    instructions="""This MCP server provides read-only access to an InfluxDB v2 database.

Available operations:
- Test database connection and get status information
- List available buckets in the InfluxDB instance
- List available measurements within a specific bucket
- Execute custom Flux queries for data analysis
- Get server configuration information
- Access sample Flux query templates for common use cases

All operations are read-only for security. Use the available tools to explore time-series data, perform analytics, and monitor your InfluxDB metrics. The server also provides resource templates for common Flux query patterns like anomaly detection, correlation analysis, and threshold monitoring.""",
    stateless_http=True,
    description="MCP server providing read-only access to InfluxDB v2 database",
)
mcp.settings.host = os.getenv("MCP_LISTEN_HOST", "127.0.0.1")
mcp.settings.port = int(os.getenv("MCP_LISTEN_PORT", "5001"))  # Default to port 5001 if not set
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http").lower()
if MCP_TRANSPORT not in ["sse", "streamable-http", "stdio"]:
    raise ValueError(
        f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Supported modes are 'sse' (deprecated), 'streamable-http' (default) and 'stdio'."
    )

# Global InfluxDB manager instance
influxdb_manager: Optional[InfluxDBManager] = None


@mcp.custom_route("/healthcheck", methods=["GET"])
async def healthcheck(request: Request) -> JSONResponse:
    """Simple healthcheck endpoint for Docker health monitoring."""
    try:
        # Test basic server availability
        server_status = {
            "status": "healthy",
            "service": "influxdb-mcp",
        }

        # Optionally test InfluxDB connection if available
        try:
            manager = get_influxdb_manager()
            connection_status = manager.test_connection()
            server_status["influxdb_status"] = connection_status["status"]
        except Exception as e:
            # Don't fail healthcheck if InfluxDB is down, just report it
            server_status["influxdb_status"] = "error"
            server_status["influxdb_error"] = str(e)

        return JSONResponse(server_status)
    except Exception as e:
        return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=503)


def get_influxdb_manager() -> InfluxDBManager:
    """Get or create InfluxDB manager instance."""
    global influxdb_manager
    if influxdb_manager is None:
        config = get_config()
        influxdb_manager = InfluxDBManager(config)
        influxdb_manager.connect()
    return influxdb_manager


@mcp.tool()
def test_connection() -> Dict[str, Any]:
    """Test the connection to InfluxDB and return detailed status information including server version and health."""
    try:
        manager = get_influxdb_manager()
        return manager.test_connection()
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def list_buckets() -> Dict[str, Any]:
    """List all available buckets in the InfluxDB instance with their retention policies and organization details."""
    try:
        manager = get_influxdb_manager()
        buckets = manager.list_buckets()

        return {"status": "success", "buckets": buckets, "count": len(buckets)}
    except Exception as e:
        logger.error(f"Failed to list buckets: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


@mcp.tool()
def list_measurements(bucket: str) -> Dict[str, Any]:
    """List all available measurements (time series) in the specified InfluxDB bucket along with their fields and tags."""
    try:
        manager = get_influxdb_manager()
        measurements = manager.list_measurements(bucket)
        return {
            "status": "success",
            "measurements": measurements,
            "count": len(measurements),
        }
    except Exception as e:
        logger.error(f"Failed to list measurements: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def execute_flux_query(query: str) -> Dict[str, Any]:
    """Execute a custom Flux query against the InfluxDB database. Supports aggregations, filtering, transformations, and analytics operations. Returns structured time-series data."""
    try:
        manager = get_influxdb_manager()
        data = manager.execute_query(query)

        return {
            "status": "success",
            "query": query,
            "data": data,
            "record_count": len(data),
        }
    except Exception as e:
        logger.error(f"Failed to execute Flux query: {e}")
        return {"status": "error", "message": str(e), "query": query}


@mcp.tool()
def get_server_info() -> Dict[str, Any]:
    """Get comprehensive information about the MCP server including version, InfluxDB configuration, and connection settings."""
    try:
        config = get_config()
        return {
            "server_name": "influxdb-mcp",
            "version": "0.1.0",
            "description": "MCP server providing read-only access to InfluxDB v2 database",
            "influxdb_config": {
                "url": config.url,
                "org": config.org,
                "use_ssl": config.use_ssl,
                "timeout": config.timeout,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return {"status": "error", "message": str(e)}


# MCP Resources - Live Data Access and Dynamic Queries
@mcp.resource(
    uri="influxdb://buckets",
    name="Available InfluxDB Buckets",
    description="Live list of all available buckets in the InfluxDB instance with metadata",
    mime_type="application/json",
)
def get_buckets_resource() -> str:
    """Returns current list of available buckets as JSON."""
    try:
        manager = get_influxdb_manager()
        buckets = manager.list_buckets()
        return json.dumps({
            "buckets": buckets,
            "count": len(buckets),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "timestamp": datetime.now().isoformat()})

@mcp.resource(
    uri="influxdb://measurements/{bucket}",
    name="Measurements in Bucket",
    description="Live list of measurements available in the specified bucket",
    mime_type="application/json",
)
def get_measurements_resource(bucket: str) -> str:
    """Returns current measurements in the specified bucket."""
    try:
        manager = get_influxdb_manager()
        measurements = manager.list_measurements(bucket)
        return json.dumps({
            "bucket": bucket,
            "measurements": measurements,
            "count": len(measurements),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "bucket": bucket, "timestamp": datetime.now().isoformat()})

@mcp.resource(
    uri="influxdb://status",
    name="InfluxDB Connection Status",
    description="Current connection status and server information",
    mime_type="application/json",
)
def get_status_resource() -> str:
    """Returns current InfluxDB connection status and server info."""
    try:
        manager = get_influxdb_manager()
        status = manager.test_connection()
        config = get_config()
        return json.dumps({
            "connection_status": status,
            "server_config": {
                "url": config.url,
                "org": config.org,
                "timeout": config.timeout
            },
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "timestamp": datetime.now().isoformat()})

@mcp.resource(
    uri="flux://templates/daily-hourly-average/{bucket}/{measurement}/{field}",
    name="Daily Hourly Average Query Template",
    description="Flux query template for hourly averages over the last day",
    mime_type="text/plain",
)
def get_daily_hourly_average_query(bucket: str, measurement: str, field: str) -> str:
    """Returns a ready-to-execute Flux query for daily hourly averages."""
    return f"""// Query: Last 1 day of data with hourly averages
// Generated: {datetime.now().isoformat()}
// Bucket: {bucket}, Measurement: {measurement}, Field: {field}

from(bucket: "{bucket}")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r._field == "{field}")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> yield(name: "hourly_average")"""


@mcp.resource(
    uri="flux://templates/weekly-summary/{bucket}/{measurement}/{field}",
    name="Weekly Daily Summary Query Template",
    description="Flux query template for weekly data with daily summaries (min, max, mean)",
    mime_type="text/plain",
)
def get_weekly_daily_summary_query(bucket: str, measurement: str, field: str) -> str:
    """Returns a ready-to-execute Flux query for weekly summaries."""
    return f"""// Query: Last 7 days with daily min/max/mean summaries
// Generated: {datetime.now().isoformat()}
// Bucket: {bucket}, Measurement: {measurement}, Field: {field}

import "experimental"

data = from(bucket: "{bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r._field == "{field}")

union(tables: [
  data |> aggregateWindow(every: 1d, fn: min, createEmpty: false) |> set(key: "_field", value: "{field}_min"),
  data |> aggregateWindow(every: 1d, fn: max, createEmpty: false) |> set(key: "_field", value: "{field}_max"),
  data |> aggregateWindow(every: 1d, fn: mean, createEmpty: false) |> set(key: "_field", value: "{field}_mean")
])
  |> sort(columns: ["_time"])
  |> yield(name: "daily_summary")"""

@mcp.resource(
    uri="flux://templates/recent-data/{bucket}/{measurement}/{field}/{duration}",
    name="Recent Data Query Template",
    description="Flux query template for retrieving recent data with configurable time range",
    mime_type="text/plain",
)
def get_recent_data_query(bucket: str, measurement: str, field: str, duration: str = "1h") -> str:
    """Returns a ready-to-execute Flux query for recent data."""
    return f"""// Query: Recent data for the last {duration}
// Generated: {datetime.now().isoformat()}
// Bucket: {bucket}, Measurement: {measurement}, Field: {field}

from(bucket: "{bucket}")
  |> range(start: -{duration})
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r._field == "{field}")
  |> sort(columns: ["_time"])
  |> yield(name: "recent_data")"""

@mcp.resource(
    uri="flux://templates/threshold-alerts/{bucket}/{measurement}/{field}/{threshold}",
    name="Threshold Alert Query Template", 
    description="Flux query template for monitoring values that exceed a specific threshold",
    mime_type="text/plain",
)
def get_threshold_alert_query(bucket: str, measurement: str, field: str, threshold: str) -> str:
    """Returns a ready-to-execute Flux query for threshold monitoring."""
    try:
        threshold_value = float(threshold)
    except ValueError:
        threshold_value = 80.0  # Default threshold
    
    return f"""// Query: Monitor values exceeding threshold of {threshold_value}
// Generated: {datetime.now().isoformat()}
// Bucket: {bucket}, Measurement: {measurement}, Field: {field}

from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r._field == "{field}")
  |> filter(fn: (r) => r._value > {threshold_value})
  |> map(fn: (r) => ({{
      r with
      alert_level: if r._value > {threshold_value * 1.5} then "critical"
                   else if r._value > {threshold_value * 1.2} then "warning"
                   else "info",
      threshold_exceeded: r._value - {threshold_value}
    }}))
  |> yield(name: "threshold_alerts")"""


@mcp.resource(
    uri="flux://templates/anomaly-detection/{bucket}/{measurement}/{field}",
    name="Anomaly Detection Query Template",
    description="Flux query template to detect statistical anomalies using standard deviation",
    mime_type="text/plain",
)
def get_anomaly_detection_query(bucket: str = "YOUR_BUCKET", measurement: str = "YOUR_MEASUREMENT", field: str = "YOUR_FIELD") -> str:
    """Returns a Flux query template for detecting statistical anomalies."""
    if bucket == "YOUR_BUCKET":
        # Return generic template
        return """// Query: Detect anomalies using statistical outliers
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', and 'YOUR_FIELD' with actual values

import "experimental/stats"

data = from(bucket: "YOUR_BUCKET")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")

// Calculate mean and standard deviation
stats = data
  |> stats.linearRegression()

// Find outliers (values beyond 2 standard deviations)
data
  |> map(fn: (r) => ({
      r with
      _anomaly: math.abs(x: r._value - stats.slope) > (2.0 * stats.stderr)
    }))
  |> filter(fn: (r) => r._anomaly == true)
  |> yield(name: "anomalies")"""
    else:
        # Return customized template
        return f"""// Query: Detect anomalies using statistical outliers
// Generated: {datetime.now().isoformat()}
// Bucket: {bucket}, Measurement: {measurement}, Field: {field}

import "experimental/stats"

data = from(bucket: "{bucket}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r._field == "{field}")

// Calculate mean and standard deviation
stats = data
  |> stats.linearRegression()

// Find outliers (values beyond 2 standard deviations)
data
  |> map(fn: (r) => ({{
      r with
      _anomaly: math.abs(x: r._value - stats.slope) > (2.0 * stats.stderr)
    }}))
  |> filter(fn: (r) => r._anomaly == true)
  |> yield(name: "anomalies")"""

@mcp.resource(
    uri="flux://templates/correlation/{bucket}/{measurement1}/{field1}/{measurement2}/{field2}",
    name="Correlation Analysis Query Template",
    description="Flux query template to analyze correlation between two measurements",
    mime_type="text/plain",
)
def get_correlation_analysis_query(bucket: str, measurement1: str, field1: str, measurement2: str, field2: str) -> str:
    """Returns a ready-to-execute Flux query for correlation analysis."""
    return f"""// Query: Analyze correlation between two measurements
// Generated: {datetime.now().isoformat()}
// Comparing {measurement1}.{field1} with {measurement2}.{field2}

import "experimental/join"

// First measurement
measurement1 = from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "{measurement1}")
  |> filter(fn: (r) => r._field == "{field1}")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)

// Second measurement
measurement2 = from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "{measurement2}")
  |> filter(fn: (r) => r._field == "{field2}")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)

// Join and calculate correlation metrics
join.time(left: measurement1, right: measurement2)
  |> map(fn: (r) => ({{
      _time: r._time,
      {field1}_value: r._value_left,
      {field2}_value: r._value_right,
      correlation: r._value_left * r._value_right,  // Simple correlation metric
      ratio: if r._value_right != 0.0 then r._value_left / r._value_right else 0.0
    }}))
  |> yield(name: "correlation")"""


def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("Starting InfluxDB MCP server...")

        # Test configuration and connection on startup
        try:
            config = get_config()
            logger.info(f"Connecting to InfluxDB at {config.url}")

            # Test connection
            manager = get_influxdb_manager()
            connection_status = manager.test_connection()

            if connection_status["status"] == "connected":
                logger.info("InfluxDB connection successful")
            else:
                logger.error(
                    f"InfluxDB connection failed: {connection_status.get('message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB connection: {e}")
            logger.warning("Server will start but InfluxDB operations may fail")

        # Start the FastMCP server
        mcp.run(transport=MCP_TRANSPORT) # type: ignore

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Clean up
        global influxdb_manager
        if influxdb_manager:
            influxdb_manager.disconnect()


if __name__ == "__main__":
    main()
