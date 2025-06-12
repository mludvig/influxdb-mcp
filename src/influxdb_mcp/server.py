"""
MCP server providing read-only access to InfluxDB v2 database.
"""

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
    instructions="""
    This MCP server provides read-only access to an InfluxDB v2 database.
    
    Available operations:
    - Test database connection
    - List available buckets
    - List available measurements
    - Execute custom Flux queries
    - Get server information
    
    All operations are read-only for security.
    """,
)
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000

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
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)}, status_code=503
        )


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
    """Test the connection to InfluxDB and return status information."""
    try:
        manager = get_influxdb_manager()
        return manager.test_connection()
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def list_buckets() -> Dict[str, Any]:
    """List all buckets, optionally filtered by organization name."""
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
    """List all available measurements in the configured InfluxDB bucket."""
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
    """Execute a custom Flux query against the InfluxDB database."""
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
    """Get information about the MCP server and its configuration."""
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
        mcp.run(transport="streamable-http")
        # mcp.run(transport="stdio")

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
