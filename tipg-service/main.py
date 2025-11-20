"""
TiPg Service - OGC Features and Tiles API for PostGIS
Serves vector tiles from PostGIS tables (admin boundaries, rivers, waterbodies, stations)
"""
import os
from contextlib import asynccontextmanager
from tipg.settings import PostgresSettings, DatabaseSettings
from tipg.factory import Endpoints
from tipg.database import connect_to_db, close_db_connection
from tipg.collections import register_collection_catalog
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

# Explicitly set TIPG_DB_SCHEMAS as JSON array for DatabaseSettings
os.environ["TIPG_DB_SCHEMAS"] = '["pgstac"]'

# Initialize settings
db_settings = DatabaseSettings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan - Connect to DB and register catalog."""
    # Create Connection Pool
    await connect_to_db(app, schemas=db_settings.schemas)

    # Register Collection Catalog (this is what was missing!)
    await register_collection_catalog(app, db_settings=db_settings)

    yield

    # Close the Connection Pool
    await close_db_connection(app)

# Create TiPg application with lifespan
app = FastAPI(
    title="FloodWatch TiPg - Vector Tiles API",
    description="OGC Features and Tiles API for East Africa Flood Watch",
    version="1.0.0",
    lifespan=lifespan,
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

# Mount TiPg endpoints
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
