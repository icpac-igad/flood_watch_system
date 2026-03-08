"""
STAC integration configuration for FloodWatch.

All settings loaded from environment variables with secure defaults.
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class STACConfig:
    """STAC/eoAPI configuration loaded from environment."""

    # pgSTAC database
    pgstac_host: str = os.getenv("PGSTAC_HOST", "eafw_pgdb")
    pgstac_port: int = int(os.getenv("PGSTAC_PORT", "5432"))
    pgstac_db: str = os.getenv("PGSTAC_DB", "pgstac")
    pgstac_user: str = os.getenv("PGSTAC_USER", "pgstac")
    pgstac_password: str = os.getenv("PGSTAC_PASSWORD", "")

    # Service URLs (internal Docker network)
    stac_api_url: str = os.getenv("STAC_API_URL", "http://eafw_stac:8080")
    titiler_url: str = os.getenv("TITILER_URL", "http://eafw_titiler:80")
    stac_browser_url: str = os.getenv("STAC_BROWSER_URL", "http://eafw_stac_browser:8085")

    # Data directories
    cog_data_dir: str = os.getenv("COG_DATA_DIR", "/data/cogs")
    raster_data_dir: str = os.getenv("RASTER_DATA_DIR", "/data/rasters")

    # Security
    stac_api_rate_limit: int = int(os.getenv("STAC_API_RATE_LIMIT", "100"))
    stac_api_key: str = os.getenv("STAC_API_KEY", "")

    # CORS
    stac_cors_origins: str = os.getenv("STAC_CORS_ORIGINS", "*")

    @property
    def pgstac_dsn(self) -> str:
        return (
            f"postgresql://{self.pgstac_user}:{self.pgstac_password}"
            f"@{self.pgstac_host}:{self.pgstac_port}/{self.pgstac_db}"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        if self.stac_cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.stac_cors_origins.split(",")]


def get_config() -> STACConfig:
    """Get the STAC configuration singleton."""
    return STACConfig()
