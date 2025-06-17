"""
InfluxDB client and operations module.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.flux_table import TableList
from influxdb_client.rest import ApiException
from .config import InfluxDBConfig

logger = logging.getLogger(__name__)


class InfluxDBManager:
    """Manages InfluxDB connections and operations."""

    def __init__(self, config: InfluxDBConfig):
        """Initialize InfluxDB manager with configuration."""
        self.config = config
        self._client: Optional[InfluxDBClient] = None
        self._query_api: Optional[QueryApi] = None
        self._organizations_api: Optional[Any] = None
        self._buckets_api: Optional[Any] = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def connect(self) -> None:
        """Establish connection to InfluxDB."""
        try:
            self._client = InfluxDBClient(
                url=self.config.url,
                token=self.config.token,
                org=self.config.org,
                timeout=self.config.timeout,
                verify_ssl=self.config.verify_ssl,
            )
            self._query_api = self._client.query_api()
            self._organizations_api = self._client.organizations_api()
            self._buckets_api = self._client.buckets_api()
            logger.info(f"Connected to InfluxDB at {self.config.url}")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise

    def disconnect(self) -> None:
        """Close InfluxDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._query_api = None
            logger.info("Disconnected from InfluxDB")

    def test_connection(self) -> Dict[str, Any]:
        """Test the InfluxDB connection and return status."""
        try:
            if not self._client:
                self.connect()

            # Simple health check - try a basic query
            if self._client:
                health = self._client.health()

                return {
                    "status": "connected",
                    "health": health.status if health else "unknown",
                    "message": (health.message if health and health.message else "Connection successful"),
                    "url": self.config.url,
                    "org": self.config.org,
                    "version": self._client.version(),
                    "build": self._client.build(),
                }
            else:
                raise RuntimeError("Failed to establish connection")

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "url": self.config.url,
                "org": self.config.org,
            }

    def execute_query(self, query: str) -> List:
        """Execute a Flux query and return results."""
        if not self._query_api:
            raise RuntimeError("Not connected to InfluxDB")

        try:
            logger.info(f"Executing query: {query}")
            result = self._query_api.query(query, org=self.config.org)
            if not result:
                logger.warning("Query returned no results")
                return []
            if isinstance(result, TableList):
                # Convert TableList to JSON
                result = json.loads(result.to_json())
            elif isinstance(result, list):
                # Convert list of records to JSON
                result = json.loads(TableList(result).to_json())

            return result

        except ApiException as e:
            logger.error(f"InfluxDB API error: {e}")
            raise RuntimeError(f"Query failed: {e}")
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise

    def list_measurements(self, bucket: str) -> List[Dict[str, Any]]:
        """Get list of available measurements in the bucket."""

        try:
            # List all measurements in a bucket using flux query
            measurements = self._query_api.query(  # type: ignore
                f"""
                import "influxdata/influxdb/schema"
                schema.measurements(bucket: "{bucket}")
            """,
                org=self.config.org,
            )
            result = []
            for measurement in measurements:
                for record in measurement.records:
                    result.append({"measurement": record.get_value(), "tags": [], "fields": []})
                    schema_query = self._query_api.query(  # type: ignore
                        f"""
                        import "influxdata/influxdb/schema"
                        schema.measurementTagKeys(bucket: "{bucket}", measurement: "{record.get_value()}")
                    """,
                        org=self.config.org,
                    )
                    for tag_record in schema_query[0].records:
                        result[-1]["tags"].append(tag_record.get_value())
                    schema_query = self._query_api.query(  # type: ignore
                        f"""
                        import "influxdata/influxdb/schema"
                        schema.measurementFieldKeys(bucket: "{bucket}", measurement: "{record.get_value()}")
                    """,
                        org=self.config.org,
                    )
                    for field_record in schema_query[0].records:
                        result[-1]["fields"].append(field_record.get_value())
            return result

        except Exception as e:
            logger.error(f"Failed to get measurements: {e}")
            raise RuntimeError(f"Failed to get measurements: {e}")

    def list_buckets(self) -> List[Dict[str, Any]]:
        """Get list of buckets, optionally filtered by organization."""
        try:
            if not self._buckets_api:
                self.connect()

            if not self._buckets_api:
                raise RuntimeError("Buckets API not available")

            # Use provided org_name or default to configured org
            buckets = self._buckets_api.find_buckets_iter(org=self.config.org)
            bucket_list = []

            for bucket in buckets:
                bucket_info = {
                    "name": bucket.name,
                    "type": bucket.type if hasattr(bucket, "type") else None,
                    "created_at": (bucket.created_at.isoformat() if bucket.created_at else None),
                    "updated_at": (bucket.updated_at.isoformat() if bucket.updated_at else None),
                }

                bucket_list.append(bucket_info)

            logger.info(f"Found {len(bucket_list)} buckets in organization '{self.config.org}'")
            return bucket_list

        except ApiException as e:
            logger.error(f"InfluxDB API error while getting buckets: {e}")
            raise RuntimeError(f"Failed to get buckets: {e}")
        except Exception as e:
            logger.error(f"Error getting buckets: {e}")
            raise
