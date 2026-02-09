"""Google Flood Forecasting API sync job.

Fetches gauges, latest flood status, gauge models, and short-horizon forecasts,
then stores a denormalized latest snapshot in gha.google_flood_points_latest.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

import requests

from .database import ingest_google_flood_points
from .logger_config import setup_logger
from .settings import GOOGLE_FLOOD_CONFIG

logger = setup_logger(__name__, 'google_flood_sync.log')

API_BASE = "https://floodforecasting.googleapis.com/v1"
API_LIMITS = {
    "gauges_search_page_size_max": 50000,
    "query_latest_flood_status_gauge_ids_max": 20000,
    "gauge_models_batch_get_names_max": 20000,
}


class GoogleFloodAPIError(RuntimeError):
    """Raised when Google Flood API call fails."""


def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _to_rfc3339(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_rfc3339(value):
    if not value or not isinstance(value, str):
        return None
    try:
        raw = value[:-1] + "+00:00" if value.endswith("Z") else value
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _extract_hybas_id(gauge_id):
    if not gauge_id:
        return None
    match = re.search(r"hybas_(\d+)", str(gauge_id).lower())
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _confidence_from_quality_flags(*flags):
    known = [flag for flag in flags if flag is not None]
    if not known:
        return "UNKNOWN", 0.5
    if all(flag is True for flag in known):
        return "HIGH", 1.0
    if any(flag is False for flag in known):
        return "LOW", 0.0
    return "UNKNOWN", 0.5


def _build_forecast_series(forecast_payload):
    """Return (series, latest_forecast_object)."""
    if not isinstance(forecast_payload, dict):
        return [], None

    forecasts = forecast_payload.get("forecasts") or []
    if not isinstance(forecasts, list) or not forecasts:
        return [], None

    def _issued_key(entry):
        return _parse_rfc3339(entry.get("issuedTime")) or datetime.min.replace(tzinfo=timezone.utc)

    latest = max(forecasts, key=_issued_key)
    ranges = latest.get("forecastRanges") or []
    if not isinstance(ranges, list):
        return [], latest

    series = []
    for item in ranges:
        try:
            value = float(item.get("value"))
        except Exception:
            continue
        date_value = item.get("forecastStartTime") or item.get("forecastEndTime")
        if not date_value:
            continue
        series.append(
            {
                "date": date_value,
                "daily_avg": value,
                "daily_max": value,
                "daily_min": value,
            }
        )

    series.sort(key=lambda rec: rec.get("date", ""))
    return series, latest


class GoogleFloodAPIClient:
    def __init__(self, api_key, timeout_seconds=120, max_retries=4, base_backoff_seconds=1.0):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds

    def _request(self, method, path, params=None, json_body=None):
        req_params = dict(params or {})
        req_params["key"] = self.api_key
        url = f"{API_BASE}/{path}"

        payload = None
        response = None
        for attempt in range(self.max_retries + 1):
            response = requests.request(
                method=method,
                url=url,
                params=req_params,
                json=json_body,
                timeout=self.timeout_seconds,
            )
            content_type = response.headers.get("Content-Type", "").lower()
            if "application/json" in content_type:
                payload = response.json()
            else:
                payload = {"raw": response.text}

            transient = response.status_code in (429, 500, 502, 503, 504)
            if transient and attempt < self.max_retries:
                wait = self.base_backoff_seconds * (2 ** attempt)
                logger.warning(
                    f"{method} {path} transient status={response.status_code}; retry {attempt + 1}/{self.max_retries} in {wait:.1f}s"
                )
                time.sleep(wait)
                continue
            break

        if not response.ok:
            raise GoogleFloodAPIError(
                f"{method} {path} failed ({response.status_code}): {str(payload)[:1000]}"
            )
        if isinstance(payload, dict) and payload.get("error"):
            raise GoogleFloodAPIError(f"{method} {path} error: {str(payload['error'])[:1000]}")
        if not isinstance(payload, dict):
            raise GoogleFloodAPIError(f"Unexpected response type for {method} {path}: {type(payload)}")
        return payload

    def search_gauges_by_area(
        self,
        region_code,
        page_size,
        include_non_quality_verified=True,
        include_gauges_without_hydro_model=True,
    ):
        page_size = min(page_size, API_LIMITS["gauges_search_page_size_max"])
        request_body = {
            "regionCode": region_code,
            "pageSize": page_size,
            "includeNonQualityVerified": include_non_quality_verified,
            "includeGaugesWithoutHydroModel": include_gauges_without_hydro_model,
        }

        gauges = []
        while True:
            data = self._request("POST", "gauges:searchGaugesByArea", json_body=request_body)
            gauges.extend(data.get("gauges", []))
            token = data.get("nextPageToken")
            if not token:
                break
            request_body["pageToken"] = token
        return gauges

    def query_latest_status(self, gauge_ids, chunk_size):
        def fetch_chunk(ids):
            params = {"gaugeIds": list(ids)}
            try:
                data = self._request("GET", "floodStatus:queryLatestFloodStatusByGaugeIds", params=params)
            except GoogleFloodAPIError as exc:
                err = str(exc)
                if any(code in err for code in ("(413)", "(414)", "(400)")) and len(ids) > 1:
                    mid = len(ids) // 2
                    return fetch_chunk(ids[:mid]) + fetch_chunk(ids[mid:])
                if "(400)" in err and len(ids) == 1:
                    logger.warning(f"Skipping gauge status for invalid gauge id: {ids[0]}")
                    return []
                raise
            return data.get("floodStatuses", [])

        chunk_size = min(chunk_size, API_LIMITS["query_latest_flood_status_gauge_ids_max"])
        rows = []
        for chunk in _chunked(gauge_ids, chunk_size):
            rows.extend(fetch_chunk(chunk))
        return rows

    def batch_get_gauge_models(self, gauge_ids, chunk_size):
        def fetch_chunk(ids):
            params = {"names": [f"gaugeModels/{gauge_id}" for gauge_id in ids]}
            try:
                data = self._request("GET", "gaugeModels:batchGet", params=params)
            except GoogleFloodAPIError as exc:
                err = str(exc)
                if any(code in err for code in ("(413)", "(414)", "(400)")) and len(ids) > 1:
                    mid = len(ids) // 2
                    return fetch_chunk(ids[:mid]) + fetch_chunk(ids[mid:])
                if "(400)" in err and len(ids) == 1:
                    logger.warning(f"Skipping gauge model for invalid gauge id: {ids[0]}")
                    return []
                raise
            return data.get("gaugeModels", [])

        chunk_size = min(chunk_size, API_LIMITS["gauge_models_batch_get_names_max"])
        rows = []
        for chunk in _chunked(gauge_ids, chunk_size):
            rows.extend(fetch_chunk(chunk))
        return rows

    def query_gauge_forecasts(self, gauge_ids, issued_time_start, issued_time_end, chunk_size):
        def fetch_chunk(ids):
            params = {
                "gaugeIds": list(ids),
                "issuedTimeStart": issued_time_start,
                "issuedTimeEnd": issued_time_end,
            }
            try:
                data = self._request("GET", "gauges:queryGaugeForecasts", params=params)
            except GoogleFloodAPIError as exc:
                err = str(exc)
                if any(code in err for code in ("(413)", "(414)", "(400)")) and len(ids) > 1:
                    mid = len(ids) // 2
                    merged = {}
                    merged.update(fetch_chunk(ids[:mid]))
                    merged.update(fetch_chunk(ids[mid:]))
                    return merged
                if "(400)" in err and len(ids) == 1:
                    logger.warning(f"Skipping gauge forecasts for invalid gauge id: {ids[0]}")
                    return {}
                raise
            return data.get("forecasts", {})

        merged = {}
        for chunk in _chunked(gauge_ids, chunk_size):
            merged.update(fetch_chunk(chunk))
        return merged


def run_google_flood_sync():
    """Entry point used by scheduler."""
    config = GOOGLE_FLOOD_CONFIG
    api_key = config.get('api_key')
    if not api_key:
        logger.warning("Google Flood sync skipped: FLOODS_API_KEY is not configured")
        return False

    region_codes = config.get('region_codes') or []
    if not region_codes:
        logger.warning("Google Flood sync skipped: no region codes configured")
        return False

    client = GoogleFloodAPIClient(
        api_key=api_key,
        timeout_seconds=config.get('request_timeout_seconds', 120),
        max_retries=config.get('max_retries', 4),
        base_backoff_seconds=config.get('base_backoff_seconds', 1.0),
    )

    logger.info(f"Fetching Google Flood gauges for region codes: {region_codes}")
    gauges_by_id = {}
    for region_code in region_codes:
        try:
            gauges = client.search_gauges_by_area(
                region_code=region_code,
                page_size=config.get('page_size', 20000),
                include_non_quality_verified=config.get('include_non_quality_verified', True),
                include_gauges_without_hydro_model=config.get('include_gauges_without_hydro_model', True),
            )
        except Exception as e:
            logger.exception(f"Failed gauge search for region {region_code}: {e}")
            continue

        logger.info(f"Region {region_code}: fetched {len(gauges)} gauges")
        for gauge in gauges:
            gauge_id = gauge.get("gaugeId")
            if not gauge_id:
                continue

            if gauge_id not in gauges_by_id:
                gauges_by_id[gauge_id] = {
                    **gauge,
                    "_region_code": region_code,
                }
                continue

            # Merge partial duplicates from overlapping country calls.
            existing = gauges_by_id[gauge_id]
            if not existing.get("countryCode") and gauge.get("countryCode"):
                existing["countryCode"] = gauge.get("countryCode")
            if not existing.get("siteName") and gauge.get("siteName"):
                existing["siteName"] = gauge.get("siteName")
            if not existing.get("river") and gauge.get("river"):
                existing["river"] = gauge.get("river")
            if existing.get("qualityVerified") is None and gauge.get("qualityVerified") is not None:
                existing["qualityVerified"] = gauge.get("qualityVerified")
            if not existing.get("location") and gauge.get("location"):
                existing["location"] = gauge.get("location")

    if not gauges_by_id:
        logger.warning("Google Flood sync: no gauges found")
        return False

    gauge_ids = list(gauges_by_id.keys())
    logger.info(f"Google Flood sync: unique gauges={len(gauge_ids)}")

    statuses = client.query_latest_status(
        gauge_ids=gauge_ids,
        chunk_size=config.get('status_chunk_size', 500),
    )
    status_by_gauge = {}
    for status in statuses:
        gauge_id = status.get("gaugeId")
        if not gauge_id:
            continue
        current = status_by_gauge.get(gauge_id)
        if current is None:
            status_by_gauge[gauge_id] = status
            continue
        existing_ts = _parse_rfc3339(current.get("issuedTime"))
        new_ts = _parse_rfc3339(status.get("issuedTime"))
        if new_ts and (existing_ts is None or new_ts > existing_ts):
            status_by_gauge[gauge_id] = status
    logger.info(f"Google Flood sync: latest statuses={len(status_by_gauge)}")

    model_ids = [
        gauge_id
        for gauge_id, gauge in gauges_by_id.items()
        if gauge.get("hasModel") is True or gauge.get("hasModels") is True
    ]
    models = []
    if model_ids:
        models = client.batch_get_gauge_models(
            gauge_ids=model_ids,
            chunk_size=config.get('model_chunk_size', 200),
        )
    model_by_gauge = {model.get("gaugeId"): model for model in models if model.get("gaugeId")}
    logger.info(f"Google Flood sync: gauge models={len(model_by_gauge)}")

    now = datetime.now(timezone.utc)
    issued_start = _to_rfc3339(now - timedelta(days=config.get('issued_lookback_days', 7)))
    issued_end = _to_rfc3339(now)
    forecasts_by_gauge = client.query_gauge_forecasts(
        gauge_ids=gauge_ids,
        issued_time_start=issued_start,
        issued_time_end=issued_end,
        chunk_size=config.get('forecast_chunk_size', 200),
    )
    logger.info(f"Google Flood sync: forecast payloads={len(forecasts_by_gauge)}")

    records = []
    for gauge_id, gauge in gauges_by_id.items():
        location = gauge.get("location") or gauge.get("gaugeLocation") or {}
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        try:
            latitude = float(latitude) if latitude is not None else None
        except Exception:
            latitude = None
        try:
            longitude = float(longitude) if longitude is not None else None
        except Exception:
            longitude = None

        status = status_by_gauge.get(gauge_id, {})
        model = model_by_gauge.get(gauge_id, {})
        forecast_payload = forecasts_by_gauge.get(gauge_id, {})
        forecast_series, latest_forecast = _build_forecast_series(forecast_payload)

        values = [item.get("daily_avg") for item in forecast_series if isinstance(item.get("daily_avg"), (float, int))]
        daily_avg = values[0] if values else None
        daily_max = max(values) if values else None
        daily_min = min(values) if values else None

        latest_issued_time = status.get("issuedTime") or (latest_forecast or {}).get("issuedTime")
        latest_issued_dt = _parse_rfc3339(latest_issued_time)
        data_date = latest_issued_dt.date() if latest_issued_dt else now.date()

        thresholds = model.get("thresholds") or {}
        hybas_id = _extract_hybas_id(gauge_id)

        quality_verified = gauge.get("qualityVerified")
        model_quality_verified = model.get("qualityVerified")
        status_quality_verified = status.get("qualityVerified")
        confidence_level, confidence_score = _confidence_from_quality_flags(
            quality_verified,
            model_quality_verified,
            status_quality_verified,
        )

        point_id = str(hybas_id) if hybas_id is not None else gauge_id
        admin_name = gauge.get("siteName") or gauge.get("river") or gauge_id

        records.append(
            {
                "gauge_id": gauge_id,
                "point_id": point_id,
                "admin_name": admin_name,
                "hybas_id": hybas_id,
                "country_code": gauge.get("countryCode"),
                "region_code": gauge.get("_region_code"),
                "source": gauge.get("source"),
                "site_name": gauge.get("siteName"),
                "river": gauge.get("river"),
                "data_date": data_date,
                "quality_verified": quality_verified,
                "model_quality_verified": model_quality_verified,
                "status_quality_verified": status_quality_verified,
                "latest_severity": status.get("severity"),
                "latest_forecast_trend": status.get("forecastTrend"),
                "latest_issued_time": latest_issued_dt,
                "threshold_alert": thresholds.get("warningLevel"),
                "threshold_alarm": thresholds.get("dangerLevel"),
                "threshold_emergency": thresholds.get("extremeDangerLevel"),
                "daily_avg": daily_avg,
                "daily_max": daily_max,
                "daily_min": daily_min,
                "forecasts_json": forecast_series,
                "gauge_value_unit": model.get("gaugeValueUnit"),
                "gauge_model_id": model.get("gaugeModelId"),
                "confidence_level": confidence_level,
                "confidence_score": confidence_score,
                "raw_status": status,
                "raw_model": model,
                "raw_forecast": latest_forecast or forecast_payload,
                "longitude": longitude,
                "latitude": latitude,
            }
        )

    success, upserted_count, pruned_count = ingest_google_flood_points(records, prune_stale=True)
    if success:
        logger.info(
            f"Google Flood sync complete: gauges={len(gauges_by_id)}, upserted={upserted_count}, pruned={pruned_count}"
        )
    else:
        logger.error("Google Flood sync failed during DB ingest")
    return success


if __name__ == "__main__":
    run_google_flood_sync()

