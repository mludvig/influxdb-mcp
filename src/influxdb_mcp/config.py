"""
Configuration module for InfluxDB MCP server.
"""

from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class InfluxDBConfig(BaseModel):
    """InfluxDB connection configuration."""

    # InfluxDB connection settings
    host: str = Field(default="localhost", description="InfluxDB host")
    port: int = Field(default=8086, description="InfluxDB port")
    token: str = Field(..., description="InfluxDB authentication token")
    org: str = Field(..., description="InfluxDB organization")

    # Optional settings
    use_ssl: bool = Field(default=False, description="Use SSL/TLS connection")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout: int = Field(default=10000, description="Request timeout in milliseconds")

    class Config:
        env_prefix = "INFLUXDB_"
        case_sensitive = False

    # Computed properties
    @property
    def url(self) -> str:
        """Generate InfluxDB URL from host, port, and SSL settings."""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"

    @field_validator("token")
    @classmethod
    def token_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("InfluxDB token cannot be empty")
        return v

    @field_validator("org")
    @classmethod
    def org_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("InfluxDB organization cannot be empty")
        return v


def get_config() -> InfluxDBConfig:
    """Get InfluxDB configuration from environment variables."""
    import os

    # Get required values from environment
    token = os.getenv("INFLUXDB_TOKEN", "")
    org = os.getenv("INFLUXDB_ORG", "")

    # Get optional values with defaults
    host = os.getenv("INFLUXDB_HOST", "localhost")
    port = int(os.getenv("INFLUXDB_PORT", "8086"))
    use_ssl = os.getenv("INFLUXDB_USE_SSL", "false").lower() in ("true", "1", "yes")
    verify_ssl = os.getenv("INFLUXDB_VERIFY_SSL", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    timeout = int(os.getenv("INFLUXDB_TIMEOUT", "5000"))  # Default timeout in milliseconds

    return InfluxDBConfig(
        host=host,
        port=port,
        token=token,
        org=org,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
        timeout=timeout,
    )
