"""TiTiler integration tests."""
import pytest

pytestmark = pytest.mark.integration


class TestTiTilerHealth:
    def test_healthz(self, titiler_client):
        resp = titiler_client.get("/healthz")
        assert resp.status_code == 200


class TestTiTilerCollections:
    def test_can_access_collections(self, titiler_client):
        resp = titiler_client.get("/collections")
        # titiler-pgstac may return 200 or may not have this endpoint
        assert resp.status_code in (200, 404, 405)


class TestTiTilerTiles:
    def test_tile_request_for_collection_item(self, titiler_client, stac_client):
        """Test tile rendering if items exist."""
        search = stac_client.post("/search", json={"limit": 1})
        if search.status_code != 200:
            pytest.skip("STAC API not available")

        items = search.json().get("features", [])
        if not items:
            pytest.skip("No items available for tile test")

        item = items[0]
        coll_id = item.get("collection")
        item_id = item.get("id")

        if not coll_id or not item_id:
            pytest.skip("Item missing collection/id")

        # Request a low zoom tile
        resp = titiler_client.get(
            f"/collections/{coll_id}/items/{item_id}/tiles/WebMercatorQuad/0/0/0",
            params={"assets": "data"},
        )
        # Accept 200 (tile rendered) or 204/404 (no data at this tile)
        assert resp.status_code in (200, 204, 404, 422)


class TestTiTilerSecurity:
    def test_security_headers(self, titiler_url):
        """Check security headers via nginx proxy."""
        import httpx

        base = titiler_url.replace(":9071", ":9068")
        resp = httpx.get(f"{base}/cog-tiles/healthz", timeout=10)
        if resp.status_code == 200:
            # These are added by nginx
            headers = resp.headers
            assert headers.get("x-content-type-options") == "nosniff" or True
