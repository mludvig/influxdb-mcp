"""
MCP server providing read-only access to InfluxDB v2 database.
"""

import os
import logging
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
MCP_PROTOCOL = os.getenv("MCP_PROTOCOL", "streamable-http").lower()
if MCP_PROTOCOL not in ["streamable-http", "stdio"]:
    raise ValueError(
        f"Invalid MCP_PROTOCOL: {MCP_PROTOCOL}. Supported modes are 'streamable-http' and 'stdio'."
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


# MCP Resources - Sample Flux Queries
@mcp.resource(
    uri="flux://queries/daily-hourly-average",
    name="Daily Hourly Average Query",
    description="Flux query to retrieve the last 1 day of a measurement with hourly averages",
    mime_type="text/plain",
)
def get_daily_hourly_average_query() -> str:
    """Returns a Flux query template for retrieving daily data with hourly averages."""
    return """// Query: Last 1 day of data with hourly averages
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', and 'YOUR_FIELD' with actual values

from(bucket: "YOUR_BUCKET")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> yield(name: "hourly_average")"""


@mcp.resource(
    uri="flux://queries/weekly-daily-summary",
    name="Weekly Daily Summary Query",
    description="Flux query to retrieve the last 7 days of data with daily summaries (min, max, mean)",
    mime_type="text/plain",
)
def get_weekly_daily_summary_query() -> str:
    """Returns a Flux query template for weekly data with daily summaries."""
    return """// Query: Last 7 days with daily min/max/mean summaries
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', and 'YOUR_FIELD' with actual values

import "experimental"

data = from(bucket: "YOUR_BUCKET")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")

union(tables: [
  data |> aggregateWindow(every: 1d, fn: min, createEmpty: false) |> set(key: "_field", value: "YOUR_FIELD_min"),
  data |> aggregateWindow(every: 1d, fn: max, createEmpty: false) |> set(key: "_field", value: "YOUR_FIELD_max"),
  data |> aggregateWindow(every: 1d, fn: mean, createEmpty: false) |> set(key: "_field", value: "YOUR_FIELD_mean")
])
  |> sort(columns: ["_time"])
  |> yield(name: "daily_summary")"""


@mcp.resource(
    uri="flux://queries/anomaly-detection",
    name="Anomaly Detection Query",
    description="Flux query to detect anomalies using statistical outliers (values beyond 2 standard deviations)",
    mime_type="text/plain",
)
def get_anomaly_detection_query() -> str:
    """Returns a Flux query template for detecting statistical anomalies."""
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


@mcp.resource(
    uri="flux://queries/top-n-values",
    name="Top N Values Query",
    description="Flux query to find the top N highest values in a time range",
    mime_type="text/plain",
)
def get_top_n_values_query() -> str:
    """Returns a Flux query template for finding top N values."""
    return """// Query: Find top N highest values in time range
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', 'YOUR_FIELD', and N with actual values

from(bucket: "YOUR_BUCKET")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")
  |> top(n: 10)  // Change 10 to desired number of top values
  |> sort(columns: ["_value"], desc: true)
  |> yield(name: "top_values")"""


@mcp.resource(
    uri="flux://queries/rate-of-change",
    name="Rate of Change Query",
    description="Flux query to calculate the rate of change between consecutive measurements",
    mime_type="text/plain",
)
def get_rate_of_change_query() -> str:
    """Returns a Flux query template for calculating rate of change."""
    return """// Query: Calculate rate of change between consecutive measurements
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', and 'YOUR_FIELD' with actual values

from(bucket: "YOUR_BUCKET")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")
  |> sort(columns: ["_time"])
  |> derivative(unit: 1m, nonNegative: false)  // Rate per minute
  |> yield(name: "rate_of_change")"""


@mcp.resource(
    uri="flux://queries/moving-average",
    name="Moving Average Query",
    description="Flux query to calculate a moving average over a specified window",
    mime_type="text/plain",
)
def get_moving_average_query() -> str:
    """Returns a Flux query template for calculating moving averages."""
    return """// Query: Calculate moving average with specified window
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', and 'YOUR_FIELD' with actual values

from(bucket: "YOUR_BUCKET")
  |> range(start: -6h)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")
  |> sort(columns: ["_time"])
  |> movingAverage(n: 5)  // 5-point moving average
  |> yield(name: "moving_average")"""


@mcp.resource(
    uri="flux://queries/downsampling",
    name="Data Downsampling Query",
    description="Flux query to downsample high-frequency data to lower frequency with aggregation",
    mime_type="text/plain",
)
def get_downsampling_query() -> str:
    """Returns a Flux query template for downsampling data."""
    return """// Query: Downsample high-frequency data to lower frequency
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', and 'YOUR_FIELD' with actual values

from(bucket: "YOUR_BUCKET")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")
  |> aggregateWindow(
      every: 5m,        // Downsample to 5-minute intervals
      fn: mean,         // Use mean aggregation (can be min, max, median, etc.)
      createEmpty: false
    )
  |> yield(name: "downsampled")"""


@mcp.resource(
    uri="flux://queries/correlation-analysis",
    name="Correlation Analysis Query",
    description="Flux query to analyze correlation between two measurements",
    mime_type="text/plain",
)
def get_correlation_analysis_query() -> str:
    """Returns a Flux query template for correlation analysis between measurements."""
    return """// Query: Analyze correlation between two measurements
// Replace bucket, measurement, and field names with actual values

import "experimental/join"

// First measurement
measurement1 = from(bucket: "YOUR_BUCKET")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "MEASUREMENT_1")
  |> filter(fn: (r) => r._field == "FIELD_1")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)

// Second measurement
measurement2 = from(bucket: "YOUR_BUCKET")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "MEASUREMENT_2")
  |> filter(fn: (r) => r._field == "FIELD_2")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)

// Join and calculate correlation
join.time(left: measurement1, right: measurement2)
  |> map(fn: (r) => ({
      _time: r._time,
      measurement1_value: r._value_left,
      measurement2_value: r._value_right,
      correlation: r._value_left * r._value_right  // Simple correlation metric
    }))
  |> yield(name: "correlation")"""


@mcp.resource(
    uri="flux://queries/threshold-monitoring",
    name="Threshold Monitoring Query",
    description="Flux query to monitor values that cross specified thresholds",
    mime_type="text/plain",
)
def get_threshold_monitoring_query() -> str:
    """Returns a Flux query template for threshold monitoring."""
    return """// Query: Monitor values crossing specified thresholds
// Replace 'YOUR_BUCKET', 'YOUR_MEASUREMENT', 'YOUR_FIELD' and thresholds with actual values

from(bucket: "YOUR_BUCKET")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "YOUR_MEASUREMENT")
  |> filter(fn: (r) => r._field == "YOUR_FIELD")
  |> map(fn: (r) => ({
      r with
      status: if r._value > 80.0 then "critical"
              else if r._value > 60.0 then "warning"
              else if r._value < 10.0 then "low"
              else "normal"
    }))
  |> filter(fn: (r) => r.status != "normal")  // Only show threshold violations
  |> yield(name: "threshold_violations")"""


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

        # Run the FastMCP server with HTTP transport (this handles its own async event loop)
        mcp.run(transport=MCP_PROTOCOL) # type: ignore

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
