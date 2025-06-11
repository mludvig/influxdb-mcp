"""
FastMCP server providing read-only access to InfluxDB v2 database.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .config import get_config, InfluxDBConfig
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
    - List available measurements
    - Get fields and tags for measurements  
    - Query recent data
    - Query data within time ranges
    - Execute custom Flux queries
    
    All operations are read-only for security.
    """
)

# Global InfluxDB manager instance
influxdb_manager: Optional[InfluxDBManager] = None


def get_influxdb_manager() -> InfluxDBManager:
    """Get or create InfluxDB manager instance."""
    global influxdb_manager
    if influxdb_manager is None:
        config = get_config()
        influxdb_manager = InfluxDBManager(config)
        influxdb_manager.connect()
    return influxdb_manager


class QueryDataRequest(BaseModel):
    """Request model for querying data within a time range."""
    measurement: str = Field(..., description="Name of the measurement to query")
    start_time: str = Field(..., description="Start time (e.g., '-1h', '2024-01-01T00:00:00Z')")
    end_time: Optional[str] = Field(None, description="End time (optional)")
    fields: Optional[List[str]] = Field(None, description="Specific fields to query (optional)")
    tags: Optional[Dict[str, str]] = Field(None, description="Tag filters (optional)")
    limit: Optional[int] = Field(None, description="Maximum number of records to return")


class FluxQueryRequest(BaseModel):
    """Request model for executing custom Flux queries."""
    query: str = Field(..., description="Flux query to execute")


@mcp.tool
def test_connection() -> Dict[str, Any]:
    """Test the connection to InfluxDB and return status information."""
    try:
        manager = get_influxdb_manager()
        return manager.test_connection()
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool
def list_measurements() -> Dict[str, Any]:
    """List all available measurements in the configured InfluxDB bucket."""
    try:
        manager = get_influxdb_manager()
        measurements = manager.get_measurements()
        return {
            "status": "success",
            "measurements": measurements,
            "count": len(measurements)
        }
    except Exception as e:
        logger.error(f"Failed to list measurements: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool
def get_measurement_schema(measurement: str) -> Dict[str, Any]:
    """Get the schema (fields and tags) for a specific measurement."""
    try:
        manager = get_influxdb_manager()
        fields = manager.get_fields(measurement)
        tags = manager.get_tags(measurement)
        
        return {
            "status": "success",
            "measurement": measurement,
            "fields": fields,
            "tags": tags,
            "field_count": len(fields),
            "tag_count": len(tags)
        }
    except Exception as e:
        logger.error(f"Failed to get schema for measurement {measurement}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "measurement": measurement
        }


@mcp.tool
def get_recent_data(measurement: str, limit: int = 100, time_range: str = "-1h") -> Dict[str, Any]:
    """Get recent data for a specific measurement."""
    try:
        manager = get_influxdb_manager()
        data = manager.get_recent_data(measurement, limit, time_range)
        
        return {
            "status": "success",
            "measurement": measurement,
            "time_range": time_range,
            "limit": limit,
            "data": data,
            "record_count": len(data)
        }
    except Exception as e:
        logger.error(f"Failed to get recent data for {measurement}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "measurement": measurement
        }


@mcp.tool
def query_data_range(
    measurement: str,
    start_time: str,
    end_time: Optional[str] = None,
    fields: Optional[List[str]] = None,
    tags: Optional[Dict[str, str]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Query data within a specific time range with optional filters."""
    try:
        manager = get_influxdb_manager()
        data = manager.query_data_range(
            measurement=measurement,
            start_time=start_time,
            end_time=end_time,
            fields=fields,
            tags=tags,
            limit=limit
        )
        
        return {
            "status": "success",
            "measurement": measurement,
            "start_time": start_time,
            "end_time": end_time,
            "filters": {
                "fields": fields,
                "tags": tags,
                "limit": limit
            },
            "data": data,
            "record_count": len(data)
        }
    except Exception as e:
        logger.error(f"Failed to query data range for {measurement}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "measurement": measurement
        }


@mcp.tool
def execute_flux_query(query: str) -> Dict[str, Any]:
    """Execute a custom Flux query against the InfluxDB database."""
    try:
        manager = get_influxdb_manager()
        data = manager.execute_query(query)
        
        return {
            "status": "success",
            "query": query,
            "data": data,
            "record_count": len(data)
        }
    except Exception as e:
        logger.error(f"Failed to execute Flux query: {e}")
        return {
            "status": "error",
            "message": str(e),
            "query": query
        }


@mcp.tool
def get_server_info() -> Dict[str, Any]:
    """Get information about the MCP server and its configuration."""
    try:
        config = get_config()
        return {
            "server_name": "influxdb-mcp",
            "version": "0.1.0",
            "description": "FastMCP server providing read-only access to InfluxDB v2 database",
            "influxdb_config": {
                "url": config.url,
                "org": config.org,
                "bucket": config.bucket,
                "use_ssl": config.use_ssl,
                "timeout": config.timeout
            },
            "capabilities": [
                "test_connection",
                "list_measurements", 
                "get_measurement_schema",
                "get_recent_data",
                "query_data_range",
                "execute_flux_query"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


async def main():
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
                logger.error(f"InfluxDB connection failed: {connection_status.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB connection: {e}")
            logger.warning("Server will start but InfluxDB operations may fail")
        
        # Run the FastMCP server
        mcp.run()
        
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
    asyncio.run(main())