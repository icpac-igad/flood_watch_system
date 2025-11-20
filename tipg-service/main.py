"""
TiPg Service - OGC Features and Tiles API for PostGIS
Serves vector tiles from PostGIS tables (admin boundaries, rivers, waterbodies, stations)
"""
import os
from tipg.settings import PostgresSettings
from tipg.factory import Endpoints
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

# Build database URL from environment
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "floodwatch_pass")
POSTGRES_DBNAME = os.getenv("POSTGRES_DBNAME", "floodwatch")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgis")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DBNAME}"

# Set DATABASE_URL environment variable for TiPg to read
os.environ["DATABASE_URL"] = DATABASE_URL

# TiPg will automatically read these from environment:
# - TIPG_DB_SCHEMAS
# - TIPG_TABLE_PATTERN
# - TIPG_EXCLUDE_TABLES
# - TIPG_EXCLUDE_FUNCTION_SCHEMAS
# So we just need to ensure they're set in docker-compose

# Create TiPg application with default settings (reads from environment)
app = FastAPI(
    title="FloodWatch TiPg - Vector Tiles API",
    description="OGC Features and Tiles API for East Africa Flood Watch",
    version="1.0.0",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

# Mount TiPg endpoints - Endpoints() will create PostgresSettings from environment
endpoints = Endpoints(
    title="FloodWatch Vector Data",
    with_tiles_viewer=True,  # Enable built-in tile viewer
)
app.include_router(endpoints.router, tags=["OGC API"])

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "tipg"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8083")),
        reload=True
    )
