"""
Database connection pool using asyncpg
Connects to existing Geomanager CMS PostgreSQL database
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from asyncpg import Pool

from eafw_api.config import get_settings

settings = get_settings()

# Global connection pool
_pool: Pool | None = None


async def create_pool() -> Pool:
    """Create database connection pool"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
    return _pool


async def close_pool():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_pool() -> Pool:
    """Get the connection pool, creating if needed"""
    global _pool
    if _pool is None:
        _pool = await create_pool()
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
