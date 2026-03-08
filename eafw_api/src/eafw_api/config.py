"""
EAFW API Configuration
Connects to the same PostgreSQL database as Geomanager CMS
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - loaded from environment variables"""

    # API Info
    app_name: str = "FloodWatch API"
    app_version: str = "0.1.0"
    app_description: str = "East Africa Flood Watch - Independent API Service"
    debug: bool = False

    # Database - connects via pgbouncer to existing CMS database
    database_host: str = "eafw_pgbouncer"
    database_port: int = 6432
    database_name: str = "geomanager_web"
    database_user: str = "geomanager"
    database_password: str = ""

    # Direct DB connection (for admin operations if needed)
    database_direct_host: str = "eafw_db"
    database_direct_port: int = 5432

    # Database pool settings
    db_pool_min_size: int = 2
    db_pool_max_size: int = 20

    # Schemas
    gha_schema: str = "gha"
    cms_schema: str = "cms"

    # CORS
    cors_origins: list[str] = ["*"]

    # Upstream CMS API base (used for compatibility proxy endpoints)
    # Can be either host root (http://eafw_cms:8000) or explicit API root
    # (http://eafw_cms:8000/api). It is normalized to include /api.
    cms_base_url: str = "http://eafw_cms:8000"
    cms_api_base_url: str = "http://eafw_cms:8000/api"
    # Host header forwarded by the API compatibility proxy when requesting CMS.
    # Needed in local docker where CMS ALLOWED_HOSTS may not include service DNS.
    cms_proxy_host_header: str = "localhost"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    class Config:
        env_prefix = "EAFW_"
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
