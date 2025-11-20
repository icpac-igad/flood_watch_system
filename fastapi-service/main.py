"""
FastAPI Service for High-Performance Deterministic Forecast Data
Designed to work alongside Django for FloodWatch system
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

import orjson
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
timing_logger = logging.getLogger('fastapi.timing')

# Database config from environment
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'postgis')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'flood_watch_system')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

db_pool: Optional[asyncpg.Pool] = None

# Simple in-memory cache
dates_cache = {'data': None, 'timestamp': None, 'ttl': 900}


def get_cache(cache_dict: Dict) -> Optional[Any]:
    """Check cache validity"""
    if cache_dict['data'] is None or cache_dict['timestamp'] is None:
        return None
    if (time.time() - cache_dict['timestamp']) > cache_dict['ttl']:
        return None
    return cache_dict['data']


def set_cache(cache_dict: Dict, data: Any):
    """Set cache with timestamp"""
    cache_dict['data'] = data
    cache_dict['timestamp'] = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    global db_pool

    logger.info("🚀 Starting FastAPI forecast service...")
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=30
        )
        async with db_pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM "Impact_mergeddeterministicgeojson"')
            logger.info(f"✅ Connected to database: {count} forecast records")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

    yield

    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


app = FastAPI(
    title="FloodWatch Forecast API",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def log_timing(endpoint: str, duration_ms: float, status: int, cached: bool = False):
    """Log with emojis"""
    emoji = '⚡' if duration_ms < 5 else '🚀' if duration_ms < 20 else '✅' if duration_ms < 100 else '⚠️'
    cache_str = ' [CACHED]' if cached else ''
    timing_logger.info(f'{emoji} GET {endpoint} - {status} - {duration_ms:.2f}ms{cache_str}')


def filter_by_country(geojson: Dict, country: str) -> Dict:
    """Filter GeoJSON features by country"""
    if not country or 'features' not in geojson:
        return geojson

    filtered = [
        f for f in geojson['features']
        if f.get('properties', {}).get('country', '').lower() == country.lower()
    ]
    return {**geojson, 'features': filtered}


@app.get("/")
async def root():
    return {
        "service": "FloodWatch Forecast API",
        "status": "operational",
        "endpoints": {
            "dates": "/api/fast/merged-forecast/dates/",
            "forecast": "/api/fast/merged-forecast/{date}/",
            "latest": "/api/fast/merged-forecast/latest/",
            "ensemble": "/api/fast/ensemble-control-points",
            "ensemble_by_date": "/api/fast/ensemble-forecast/{date}/",
            "ensemble_dates": "/api/fast/ensemble-forecast-dates/"
        }
    }


@app.get("/api/fast/ensemble-control-points")
async def get_ensemble_control_points(response: Response):
    """Get all ensemble control points with forecast data (latest date)"""
    start = time.time()

    try:
        async with db_pool.acquire() as conn:
            # Get the latest ensemble forecast GeoJSON
            row = await conn.fetchrow('''
                SELECT geojson_data, data_date, feature_count, features_with_data, updated_at
                FROM impact_ensemble_forecast_geojson
                ORDER BY data_date DESC
                LIMIT 1
            ''')

            if not row:
                raise HTTPException(404, "No ensemble forecast data available")

            geojson_data = row['geojson_data']

            duration_ms = (time.time() - start) * 1000
            log_timing('/api/fast/ensemble-control-points', duration_ms, 200, False)

            response.headers['X-Feature-Count'] = str(row['feature_count'])
            response.headers['X-Features-With-Data'] = str(row['features_with_data'])
            response.headers['X-Forecast-Date'] = row['data_date'].isoformat()
            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
            response.headers['Cache-Control'] = 'public, max-age=3600'

            return geojson_data

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_timing('/api/fast/ensemble-control-points', duration_ms, 500, False)
        logger.error(f"Error fetching ensemble control points: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fast/ensemble-forecast/{date}/")
async def get_ensemble_forecast_by_date(date: str, response: Response):
    """Get ensemble forecast for a specific date (YYYY-MM-DD)"""
    start = time.time()

    try:
        # Convert date string to date object
        from datetime import datetime as dt
        date_obj = dt.strptime(date, '%Y-%m-%d').date()

        async with db_pool.acquire() as conn:
            # Get ensemble forecast for specific date
            row = await conn.fetchrow('''
                SELECT geojson_data, data_date, feature_count, features_with_data, updated_at
                FROM impact_ensemble_forecast_geojson
                WHERE data_date = $1
            ''', date_obj)

            if not row:
                raise HTTPException(404, f"No ensemble forecast data available for {date}")

            geojson_data = row['geojson_data']

            duration_ms = (time.time() - start) * 1000
            log_timing(f'/api/fast/ensemble-forecast/{date}/', duration_ms, 200, False)

            response.headers['X-Feature-Count'] = str(row['feature_count'])
            response.headers['X-Features-With-Data'] = str(row['features_with_data'])
            response.headers['X-Forecast-Date'] = row['data_date'].isoformat()
            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
            response.headers['Cache-Control'] = 'public, max-age=3600'

            return geojson_data

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_timing(f'/api/fast/ensemble-forecast/{date}/', duration_ms, 500, False)
        logger.error(f"Error fetching ensemble forecast for {date}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fast/ensemble-forecast-dates/")
async def get_ensemble_forecast_dates(response: Response):
    """Get all available ensemble forecast dates"""
    start = time.time()

    try:
        async with db_pool.acquire() as conn:
            # Get all available dates
            rows = await conn.fetch('''
                SELECT data_date, feature_count, features_with_data
                FROM impact_ensemble_forecast_geojson
                ORDER BY data_date DESC
            ''')

            dates_data = [
                {
                    'date': row['data_date'].isoformat(),
                    'feature_count': row['feature_count'],
                    'features_with_data': row['features_with_data']
                }
                for row in rows
            ]

            duration_ms = (time.time() - start) * 1000
            log_timing('/api/fast/ensemble-forecast-dates/', duration_ms, 200, False)

            response.headers['X-Total-Dates'] = str(len(dates_data))
            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
            response.headers['Cache-Control'] = 'public, max-age=300'

            return {"dates": dates_data}

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_timing('/api/fast/ensemble-forecast-dates/', duration_ms, 500, False)
        logger.error(f"Error fetching ensemble forecast dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/fast/merged-forecast/dates/")
async def get_dates(response: Response):
    """List available forecast dates"""
    start = time.time()

    # Check cache
    cached = get_cache(dates_cache)
    if cached:
        duration_ms = (time.time() - start) * 1000
        log_timing('/dates/', duration_ms, 200, True)
        response.headers['X-Cache-Hit'] = 'true'
        response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
        return cached

    # Query database
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT data_date, date_string, feature_count, file_count, created_at
                FROM "Impact_mergeddeterministicgeojson"
                ORDER BY data_date DESC
            ''')

            # Filter out invalid dates and build list
            dates_list = []
            for r in rows:
                # Validate date before adding to list
                try:
                    date_str = r['date_string']
                    if date_str:
                        # Validate date string format and that it represents a real date
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        # Ensure round-trip conversion matches (catches overflow dates like 20251184)
                        if date_obj.strftime('%Y%m%d') != date_str:
                            logger.warning(f"Skipping invalid date from DB: {date_str}")
                            continue

                    dates_list.append({
                        'date': r['data_date'].isoformat(),
                        'date_string': date_str,
                        'feature_count': r['feature_count'],
                        'file_count': r['file_count'],
                        'created_at': r['created_at'].isoformat() if r['created_at'] else None
                    })
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Skipping invalid date record: {r.get('date_string')} - {e}")
                    continue

            result = {'dates': dates_list, 'count': len(dates_list), 'source': 'database'}
            set_cache(dates_cache, result)

            duration_ms = (time.time() - start) * 1000
            log_timing('/dates/', duration_ms, 200, False)
            response.headers['X-Cache-Hit'] = 'false'
            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
            return result

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_timing('/dates/', duration_ms, 500, False)
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fast/merged-forecast/{forecast_date}/")
async def get_forecast(
    forecast_date: str,
    response: Response,
    country: Optional[str] = Query(None)
):
    """Get forecast for specific date"""
    start = time.time()

    # Validate date
    try:
        date_obj = datetime.strptime(forecast_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(400, f"Invalid date: {forecast_date}")

    try:
        async with db_pool.acquire() as conn:
            # Query specific date
            row = await conn.fetchrow('''
                SELECT geojson_data, data_date, feature_count, updated_at
                FROM "Impact_mergeddeterministicgeojson"
                WHERE data_date = $1
            ''', date_obj)

            if not row:
                # Fallback to latest
                row = await conn.fetchrow('''
                    SELECT geojson_data, data_date, feature_count, updated_at
                    FROM "Impact_mergeddeterministicgeojson"
                    ORDER BY data_date DESC LIMIT 1
                ''')

                if not row:
                    raise HTTPException(404, f"No data for {forecast_date}")

                response.headers['X-Fallback'] = 'true'
                response.headers['X-Fallback-Date'] = row['data_date'].isoformat()

            geojson = row['geojson_data']
            # Parse if it's a string (shouldn't be needed with JSONB, but safety check)
            if isinstance(geojson, str):
                geojson = orjson.loads(geojson)

            original_count = len(geojson.get('features', []))

            # Filter by country
            if country:
                geojson = filter_by_country(geojson, country)

            duration_ms = (time.time() - start) * 1000
            log_timing(f'/{forecast_date}/', duration_ms, 200, False)

            # Headers
            response.headers['X-Forecast-Date'] = row['data_date'].isoformat()
            response.headers['X-Feature-Count'] = str(len(geojson.get('features', [])))
            response.headers['X-Original-Count'] = str(original_count)
            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
            response.headers['Cache-Control'] = 'public, max-age=3600'

            return geojson

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_timing(f'/{forecast_date}/', duration_ms, 500, False)
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fast/merged-forecast/latest/")
async def get_latest(
    response: Response,
    country: Optional[str] = Query(None)
):
    """Get latest forecast"""
    start = time.time()

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT geojson_data, data_date, feature_count, updated_at
                FROM "Impact_mergeddeterministicgeojson"
                ORDER BY data_date DESC LIMIT 1
            ''')

            if not row:
                raise HTTPException(404, "No forecast data available")

            geojson = row['geojson_data']
            # Parse if it's a string (shouldn't be needed with JSONB, but safety check)
            if isinstance(geojson, str):
                geojson = orjson.loads(geojson)

            original_count = len(geojson.get('features', []))

            if country:
                geojson = filter_by_country(geojson, country)

            duration_ms = (time.time() - start) * 1000
            log_timing('/latest/', duration_ms, 200, False)

            response.headers['X-Forecast-Date'] = row['data_date'].isoformat()
            response.headers['X-Feature-Count'] = str(len(geojson.get('features', [])))
            response.headers['X-Original-Count'] = str(original_count)
            response.headers['X-Response-Time'] = f'{duration_ms:.2f}ms'
            response.headers['Cache-Control'] = 'public, max-age=1800'

            return geojson

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_timing('/latest/', duration_ms, 500, False)
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
