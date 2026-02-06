# EAFW API - FloodWatch FastAPI Service

**Author:** Hillary Koros
**Organization:** ICPAC (IGAD Climate Prediction and Applications Centre)

Independent, high-performance API service for East Africa Flood Watch system.

## Features

- **Fast & Async**: Built on FastAPI with asyncpg for high performance
- **Rate Limited**: External users rate limited, internal services unlimited
- **API Key Auth**: External access requires API key
- **Auto Documentation**: OpenAPI/Swagger docs at `/api/docs`
- **Versioned API**: v1 endpoints at `/api/v1/`

## Endpoints

### CMS Content (`/api/v1/cms/`)
- `GET /homepage` - Homepage configuration
- `GET /navbar` - Navigation bar
- `GET /footer` - Footer content
- `GET /theme` - Site theme colors
- `GET /languages` - Enabled languages
- `GET /categories` - Map layer categories

### Datasets (`/api/v1/datasets/`)
- `GET /` - List all datasets
- `GET /{id}` - Get dataset by ID
- `GET /slug/{slug}` - Get dataset by slug

### Boundaries (`/api/v1/boundaries/`)
- `GET /countries` - List countries
- `GET /countries/{gid_0}/regions` - List regions
- `GET /countries/{gid_0}/regions/{gid_1}/districts` - List districts
- `GET /admin0` - Admin0 GeoJSON
- `GET /admin1` - Admin1 GeoJSON
- `GET /admin2` - Admin2 GeoJSON

### Expert Assessments (`/api/v1/assessments/`)
- `GET /expert` - List expert assessments
- `POST /expert` - Create assessment
- `GET /expert/{id}` - Get assessment
- `PATCH /expert/{id}/publish` - Publish assessment
- `GET /districts` - District risk levels
- `POST /districts` - Set district risk
- `GET /districts/summary` - Risk summary by country

### Forecasts (`/api/v1/forecasts/`)
- `GET /control-points` - List forecast points
- `GET /control-points/{id}` - Get point details
- `GET /data` - List forecast data
- `GET /data/{point_id}/timeseries` - Point timeseries
- `GET /available-dates` - Available forecast dates

### Bulletins (`/api/v1/bulletins/`)
- `GET /` - List bulletins
- `POST /` - Create bulletin
- `GET /{id}` - Get bulletin
- `PATCH /{id}/publish` - Publish bulletin
- `GET /latest/summary` - Latest bulletin for homepage

## Configuration

Environment variables (prefix: `EAFW_`):

```bash
EAFW_DATABASE_HOST=eafw_pgbouncer
EAFW_DATABASE_PORT=6432
EAFW_DATABASE_NAME=geomanager_web
EAFW_DATABASE_USER=geomanager
EAFW_DATABASE_PASSWORD=your_password
EAFW_DEBUG=false
```

## Running

### Docker
```bash
docker build -t eafw-api .
docker run -p 9060:9060 --env-file .env eafw-api
```

### Development
```bash
cd eafw_api
pip install -e ".[dev]"
uvicorn eafw_api.app:app --reload --port 9060
```

## Rate Limiting

- **Internal services** (eafw_cms, eafw_mapviewer, etc.): Unlimited
- **External users**: 100 requests per 60 seconds
- Rate limit headers included in responses

## Authentication

- **Internal**: No auth required (trusted hosts)
- **External**: API key required in `X-API-Key` header

## License

MIT
