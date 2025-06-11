"""
InfluxDB client and operations module.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
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
                verify_ssl=self.config.verify_ssl
            )
            self._query_api = self._client.query_api()
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
                    "message": health.message if health and health.message else "Connection successful",
                    "url": self.config.url,
                    "org": self.config.org,
                    "bucket": self.config.bucket
                }
            else:
                raise RuntimeError("Failed to establish connection")
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "url": self.config.url,
                "org": self.config.org,
                "bucket": self.config.bucket
            }
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a Flux query and return results."""
        if not self._query_api:
            raise RuntimeError("Not connected to InfluxDB")
        
        try:
            logger.info(f"Executing query: {query}")
            result = self._query_api.query(query)
            
            # Convert result to list of dictionaries
            records = []
            for table in result:
                for record in table.records:
                    record_dict = {
                        "time": record.get_time(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value()
                    }
                    # Add tags
                    if record.values:
                        for key, value in record.values.items():
                            if key.startswith("_") or key in ["result", "table"]:
                                continue
                            record_dict[key] = value
                    
                    records.append(record_dict)
            
            logger.info(f"Query returned {len(records)} records")
            return records
            
        except ApiException as e:
            logger.error(f"InfluxDB API error: {e}")
            raise RuntimeError(f"Query failed: {e}")
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def get_measurements(self) -> List[str]:
        """Get list of available measurements in the bucket."""
        query = f'''
        import "influxdata/influxdb/schema"
        
        schema.measurements(bucket: "{self.config.bucket}")
        '''
        
        try:
            results = self.execute_query(query)
            measurements = [record.get("_value", "") for record in results if record.get("_value")]
            return sorted(list(set(measurements)))
        except Exception as e:
            logger.error(f"Failed to get measurements: {e}")
            return []
    
    def get_fields(self, measurement: str) -> List[str]:
        """Get list of fields for a specific measurement."""
        query = f'''
        import "influxdata/influxdb/schema"
        
        schema.fieldKeys(
            bucket: "{self.config.bucket}",
            predicate: (r) => r._measurement == "{measurement}"
        )
        '''
        
        try:
            results = self.execute_query(query)
            fields = [record.get("_value", "") for record in results if record.get("_value")]
            return sorted(list(set(fields)))
        except Exception as e:
            logger.error(f"Failed to get fields for measurement {measurement}: {e}")
            return []
    
    def get_tags(self, measurement: str) -> Dict[str, List[str]]:
        """Get list of tag keys and their values for a specific measurement."""
        query = f'''
        import "influxdata/influxdb/schema"
        
        schema.tagKeys(
            bucket: "{self.config.bucket}",
            predicate: (r) => r._measurement == "{measurement}"
        )
        '''
        
        try:
            results = self.execute_query(query)
            tag_keys = [record.get("_value", "") for record in results if record.get("_value")]
            
            # Get values for each tag key
            tags = {}
            for tag_key in tag_keys:
                if tag_key:
                    tag_values_query = f'''
                    import "influxdata/influxdb/schema"
                    
                    schema.tagValues(
                        bucket: "{self.config.bucket}",
                        tag: "{tag_key}",
                        predicate: (r) => r._measurement == "{measurement}"
                    )
                    '''
                    try:
                        tag_results = self.execute_query(tag_values_query)
                        values = [record.get("_value", "") for record in tag_results if record.get("_value")]
                        tags[tag_key] = sorted(list(set(values)))
                    except Exception as e:
                        logger.warning(f"Failed to get values for tag {tag_key}: {e}")
                        tags[tag_key] = []
            
            return tags
        except Exception as e:
            logger.error(f"Failed to get tags for measurement {measurement}: {e}")
            return {}
    
    def get_recent_data(self, measurement: str, limit: int = 100, 
                       time_range: str = "-1h") -> List[Dict[str, Any]]:
        """Get recent data for a measurement."""
        query = f'''
        from(bucket: "{self.config.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> limit(n: {limit})
            |> sort(columns: ["_time"], desc: true)
        '''
        
        return self.execute_query(query)
    
    def query_data_range(self, measurement: str, start_time: str, 
                        end_time: Optional[str] = None, 
                        fields: Optional[List[str]] = None,
                        tags: Optional[Dict[str, str]] = None,
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query data within a time range with optional filters."""
        
        # Build time range
        time_filter = f'range(start: {start_time}'
        if end_time:
            time_filter += f', stop: {end_time}'
        time_filter += ')'
        
        # Build measurement filter
        filters = [f'r._measurement == "{measurement}"']
        
        # Add field filters
        if fields:
            field_conditions = [f'r._field == "{field}"' for field in fields]
            filters.append(f'({" or ".join(field_conditions)})')
        
        # Add tag filters
        if tags:
            for tag_key, tag_value in tags.items():
                filters.append(f'r.{tag_key} == "{tag_value}"')
        
        filter_clause = ' and '.join(filters)
        
        # Build query
        query = f'''
        from(bucket: "{self.config.bucket}")
            |> {time_filter}
            |> filter(fn: (r) => {filter_clause})
            |> sort(columns: ["_time"], desc: true)
        '''
        
        if limit:
            query += f'\n    |> limit(n: {limit})'
        
        return self.execute_query(query)
