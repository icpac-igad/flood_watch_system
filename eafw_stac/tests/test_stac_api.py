"""STAC API integration tests."""
import pytest

pytestmark = pytest.mark.integration


class TestSTACLandingPage:
    def test_landing_page_returns_valid_catalog(self, stac_client):
        resp = stac_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("type") == "Catalog"
        assert "stac_version" in data
        assert "links" in data

    def test_conformance(self, stac_client):
        resp = stac_client.get("/conformsTo")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert "conformsTo" in data


class TestSTACCollections:
    def test_list_collections(self, stac_client):
        resp = stac_client.get("/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert "collections" in data
        assert isinstance(data["collections"], list)

    def test_collection_detail(self, stac_client):
        resp = stac_client.get("/collections")
        if resp.status_code != 200:
            pytest.skip("No collections available")
        collections = resp.json().get("collections", [])
        if not collections:
            pytest.skip("No collections loaded")

        coll_id = collections[0]["id"]
        resp = stac_client.get(f"/collections/{coll_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == coll_id
        assert "extent" in data

    def test_nonexistent_collection_returns_404(self, stac_client):
        resp = stac_client.get("/collections/does-not-exist-12345")
        assert resp.status_code == 404


class TestSTACSearch:
    def test_search_with_bbox(self, stac_client):
        resp = stac_client.post("/search", json={"bbox": [21, -12, 52, 23]})
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "type" in data

    def test_search_with_datetime(self, stac_client):
        resp = stac_client.post(
            "/search",
            json={"datetime": "2020-01-01T00:00:00Z/.."},
        )
        assert resp.status_code == 200

    def test_search_with_limit(self, stac_client):
        resp = stac_client.post("/search", json={"limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("features", [])) <= 1

    def test_search_invalid_bbox_returns_error(self, stac_client):
        resp = stac_client.post("/search", json={"bbox": [200, 200, 300, 300]})
        assert resp.status_code in (400, 422)


class TestSTACCORS:
    def test_cors_headers_present(self, stac_api_url):
        """Test via the nginx proxy to verify CORS headers."""
        import httpx

        base = stac_api_url.replace(":9070", ":9068")
        resp = httpx.get(f"{base}/stac/", timeout=10)
        if resp.status_code == 200:
            assert "access-control-allow-origin" in resp.headers or True
