# STAC API + EAOPI Integration & FastAPI Migration Roadmap

## Phase 1: STAC Collections Setup (1-2 weeks)

### 1.1 Create STAC Collections Metadata

#### Collection 1: Deterministic Forecasts
```json
{
  "id": "flood_forecasts_deterministic",
  "description": "High-resolution deterministic flood forecasts from ICPAC",
  "extent": {
    "spatial": {
      "bbox": [[25.0, -15.0, 55.0, 15.0]]
    },
    "temporal": {
      "interval": [["2020-01-01", null]]
    }
  }
}
```

#### Collection 2: Ensemble Forecasts (EAOPI/GeoSFM)
```json
{
  "id": "flood_forecasts_ensemble",
  "description": "Multi-model ensemble flood forecasts from GeoSFM/EAOPI",
  "extent": {
    "spatial": {
      "bbox": [[25.0, -15.0, 55.0, 15.0]]
    }
  }
}
```

### 1.2 Implementation Steps

**A. Define Collections in Database**
- Create collections via STAC API POST endpoint
- Or insert directly into pgstac.collections table
- Verify with: GET /collections

**B. Create Registration Script**
- Script: stac-api/register_collections.py
- Registers initial collections on startup
- Idempotent (safe to run multiple times)

---

## Phase 2: STAC Item Ingestion (2-3 weeks)

### 2.1 Deterministic Forecast Items

**Source:** Impact_mergeddeterministicgeojson table

**Item Management Command:**
```bash
python manage.py ingest_stac_deterministic
python manage.py ingest_stac_ensemble --date 2025-11-06
```

**Result:**
- Creates STAC Item for each forecast date
- Stores in pgstac.items table
- Makes searchable via /search endpoint
- Temporal indexing for date range queries

### 2.2 Ensemble Forecast Items

**Source:** sync_ensemble_to_db command output

**Enhancement:**
- Modify sync_ensemble_to_db to also create STAC items
- One item per ensemble forecast date
- Link to ensemble control points
- Include model metadata (GeoSFM, ensemble members)

---

## Phase 3: Frontend Integration (1-2 weeks)

### 3.1 Update endpoints.ts Configuration

```typescript
VITE_STAC_URL=http://localhost:8081
VITE_TIPG_URL=http://localhost:8083
```

### 3.2 Create Integration Hooks

- useStacSearch - Search STAC items by collection/date/bbox
- useStacCollections - List available collections
- useTipgFeatures - Get features from TiPg
- useTipgTiles - Load vector tiles

### 3.3 Update MapViewer Component

- Add STAC collection selector to sidebar
- Display search results as layer on map
- Show ensemble data when selected
- Toggle between FastAPI and TiPg data sources

---

## Phase 4: TiPg Service Exposure (1 week)

### 4.1 Docker Compose Configuration

Add TiPg service to docker-compose.yml
- Port 8083
- Environment: DATABASE_URL pointing to postgis
- Health check: /health endpoint
- Networks: floodwatch_network

### 4.2 Verify Service

```bash
curl http://localhost:8083/collections
curl http://localhost:8083/health
```

### 4.3 Frontend Environment

Add to docker-compose environment variables:
```yaml
VITE_TIPG_URL=http://localhost:8083
VITE_STAC_URL=http://localhost:8081
```

---

## Phase 5: FastAPI to TiPg Migration (2-3 weeks)

### 5.1 Assessment

**Functions to Keep in FastAPI:**
- Custom aggregations
- Time-series analysis
- Specialized calculations

**Functions to Move to TiPg:**
- GeoJSON feature serving
- Vector tile generation
- Standard OGC API queries

### 5.2 Migration Path

1. **Parallel Operation** - Run both FastAPI and TiPg
2. **Gradual Shift** - Update frontend to prefer TiPg
3. **Performance Test** - Benchmark both implementations
4. **Full Migration** - Disable FastAPI when TiPg ready
5. **Cleanup** - Optional: Remove FastAPI service

### 5.3 Implementation

- Keep both services running during transition
- Create adapter layer in frontend for compatibility
- Monitor performance metrics
- Rollback capability if issues arise

---

## Phase 6: EAOPI Data Integration (2 weeks)

### 6.1 Ensemble Data Integration

**Current Status:**
- Ensemble sync scripts working
- Data stored in database
- Not yet indexed in STAC

**Required Changes:**
- Create STAC Collection for ensemble
- Ingest ensemble items into PgSTAC
- Enable temporal search
- Create TiPg table for ensemble features

### 6.2 Frontend Display

- Show ensemble forecasts in map viewer
- Enable multi-model comparison
- Display uncertainty bands
- Link to source data

---

## Implementation Checklist

### Collections & Items Setup
- [ ] Define STAC collection JSONs
- [ ] Register collections via API
- [ ] Create deterministic items ingestion
- [ ] Create ensemble items ingestion
- [ ] Test /search endpoint

### Frontend Preparation  
- [ ] Update endpoints.ts for STAC/TiPg URLs
- [ ] Create STAC search hooks
- [ ] Create TiPg feature hooks
- [ ] Add UI for collection selection
- [ ] Test data retrieval

### Service Configuration
- [ ] Add TiPg to docker-compose.yml
- [ ] Verify TiPg /collections endpoint
- [ ] Verify TiPg /tiles endpoint
- [ ] Add health checks

### Migration
- [ ] Benchmark FastAPI performance
- [ ] Benchmark TiPg performance
- [ ] Update frontend data sources
- [ ] Monitor for regressions
- [ ] Deprecate FastAPI if suitable

### EAOPI Integration
- [ ] Enhance sync_ensemble_to_db
- [ ] Create ensemble STAC items
- [ ] Test ensemble search
- [ ] Display ensemble on frontend
- [ ] Verify data freshness

---

## Testing Plan

### Unit Tests
- Collection registration
- Item creation and indexing
- STAC search functionality
- TiPg feature retrieval

### Integration Tests
- Full STAC API workflow
- Frontend data fetching
- Database consistency
- Cache invalidation

### Performance Tests
- Response time comparison
- Concurrent request handling
- Large dataset handling
- Vector tile rendering

---

## Success Metrics

1. STAC API operational with 50+ items
2. TiPg serving 6+ collections
3. Frontend displays STAC + TiPg data
4. Ensemble data searchable and visible
5. FastAPI performance parity with TiPg
6. Sub-500ms response times
7. 99%+ availability

---

## Timeline

Total: 10-14 weeks

- Phase 1: 1-2 weeks
- Phase 2: 2-3 weeks  
- Phase 3: 1-2 weeks
- Phase 4: 1 week
- Phase 5: 2-3 weeks
- Phase 6: 2 weeks

