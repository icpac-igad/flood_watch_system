"""
STAC sync utility — keeps pgSTAC in sync with CMS raster uploads.

When a LayerRasterFile is saved or deleted in the CMS, this module
upserts or removes the corresponding STAC item in pgSTAC so that
TiTiler can serve tiles for all raster data regardless of upload path.
"""
import json
import logging
import threading
from pathlib import Path

from django.conf import settings
from django.db import connection

logger = logging.getLogger("geomanager.stac_sync")

# Map CMS dataset/layer keywords to STAC collection IDs.
# Keys are matched case-insensitively against layer or dataset titles.
COLLECTION_MAP = {
    "cropland": "asap-cropland",
    "rangeland": "asap-rangeland",
    "landscan": "landscan-population",
    "population": "landscan-population",
    "return period": "flood-extent-return-periods",
    "flood extent": "flood-extent-return-periods",
    "daily rainfall": "wrf-daily-rainfall",
    "total rainfall": "wrf-daily-rainfall",
}

# Default COG public prefix (how TiTiler resolves asset hrefs)
COG_PUBLIC_PREFIX = getattr(settings, "STAC_COG_PUBLIC_PREFIX", "/stac-cogs")


def map_to_collection(layer_title, dataset_title=""):
    """Map a CMS layer/dataset title to a STAC collection ID."""
    text = f"{layer_title} {dataset_title}".lower()
    for keyword, collection_id in COLLECTION_MAP.items():
        if keyword in text:
            return collection_id
    return None


def _build_stac_item(item_id, collection_id, bbox, geometry, dt_str, asset_href):
    """Build a minimal STAC 1.0.0 item dict."""
    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": item_id,
        "collection": collection_id,
        "geometry": geometry,
        "bbox": bbox,
        "properties": {
            "datetime": dt_str,
        },
        "assets": {
            "data": {
                "href": asset_href,
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data"],
            }
        },
        "links": [],
    }


def _extract_raster_bounds(file_path):
    """Extract bbox and geometry from a raster file using rasterio."""
    try:
        import rasterio
    except ImportError:
        logger.warning("rasterio not installed — cannot extract raster bounds")
        return None, None

    try:
        with rasterio.open(file_path) as ds:
            b = ds.bounds
            bbox = [float(b.left), float(b.bottom), float(b.right), float(b.top)]
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]],
                ]],
            }
            return bbox, geometry
    except Exception as e:
        logger.error(f"Failed to read raster bounds: {e}")
        return None, None


def _ensure_collection(cursor, collection_id, title=""):
    """Create a pgSTAC collection if it doesn't exist."""
    cursor.execute(
        "SELECT 1 FROM pgstac.collections WHERE id = %s", [collection_id]
    )
    if cursor.fetchone():
        return

    content = json.dumps({
        "id": collection_id,
        "type": "Collection",
        "stac_version": "1.0.0",
        "title": title or collection_id,
        "description": f"Auto-created from CMS upload for {collection_id}",
        "license": "CC-BY-4.0",
        "extent": {
            "spatial": {"bbox": [[21, -12, 52, 23]]},
            "temporal": {"interval": [["2023-01-01T00:00:00Z", None]]},
        },
        "links": [],
    })
    try:
        cursor.execute("SELECT pgstac.create_collection(%s::jsonb)", [content])
        logger.info(f"Created STAC collection: {collection_id}")
    except Exception as e:
        logger.warning(f"Could not create collection {collection_id}: {e}")


def upsert_stac_item(item_dict):
    """Upsert a STAC item into pgSTAC using the database's upsert_item function."""
    item_json = json.dumps(item_dict)
    with connection.cursor() as cursor:
        _ensure_collection(cursor, item_dict["collection"])
        cursor.execute("SELECT pgstac.upsert_item(%s::jsonb)", [item_json])
    logger.info(f"Upserted STAC item: {item_dict['collection']}/{item_dict['id']}")


def delete_stac_item(collection_id, item_id):
    """Delete a STAC item from pgSTAC."""
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM pgstac.items WHERE collection = %s AND id = %s",
            [collection_id, item_id],
        )
    logger.info(f"Deleted STAC item: {collection_id}/{item_id}")


def sync_layer_raster_file(layer_raster_file):
    """Sync a LayerRasterFile instance to pgSTAC.

    Called from the post_save signal handler.
    """
    layer = layer_raster_file.layer
    dataset_title = ""
    if hasattr(layer, "dataset") and layer.dataset:
        dataset_title = layer.dataset.title or ""

    collection_id = map_to_collection(layer.title, dataset_title)
    if not collection_id:
        logger.debug(f"No STAC collection mapping for layer '{layer.title}' — skipping sync")
        return

    file_path = layer_raster_file.file.path
    if not Path(file_path).exists():
        logger.warning(f"Raster file not found: {file_path}")
        return

    bbox, geometry = _extract_raster_bounds(file_path)
    if not bbox:
        # Fallback to GHoA extent
        bbox = [21.0, -12.0, 52.0, 23.0]
        geometry = {
            "type": "Polygon",
            "coordinates": [[[21, -12], [52, -12], [52, 23], [21, 23], [21, -12]]],
        }

    dt = layer_raster_file.time
    dt_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    item_id = f"cms-{collection_id}-{dt.strftime('%Y%m%d%H%M%S')}"

    # Build asset href relative to COG public prefix
    rel_path = Path(file_path).name
    asset_href = f"{COG_PUBLIC_PREFIX}/{collection_id}/{rel_path}"

    item = _build_stac_item(item_id, collection_id, bbox, geometry, dt_str, asset_href)
    upsert_stac_item(item)


def sync_to_stac_async(layer_raster_file_pk):
    """Run STAC sync in a background thread to avoid blocking the CMS save."""
    def _sync():
        try:
            from geomanager.models import LayerRasterFile
            instance = LayerRasterFile.objects.select_related("layer", "layer__dataset").get(pk=layer_raster_file_pk)
            sync_layer_raster_file(instance)
        except Exception as e:
            logger.error(f"STAC sync failed for LayerRasterFile pk={layer_raster_file_pk}: {e}", exc_info=True)

    thread = threading.Thread(target=_sync, daemon=True)
    thread.start()


def remove_from_stac_async(layer_raster_file):
    """Remove STAC item in a background thread before CMS deletion."""
    layer = layer_raster_file.layer
    dataset_title = ""
    if hasattr(layer, "dataset") and layer.dataset:
        dataset_title = layer.dataset.title or ""

    collection_id = map_to_collection(layer.title, dataset_title)
    if not collection_id:
        return

    dt = layer_raster_file.time
    item_id = f"cms-{collection_id}-{dt.strftime('%Y%m%d%H%M%S')}"

    def _delete():
        try:
            delete_stac_item(collection_id, item_id)
        except Exception as e:
            logger.error(f"STAC delete failed for {collection_id}/{item_id}: {e}", exc_info=True)

    thread = threading.Thread(target=_delete, daemon=True)
    thread.start()
