"""Health check tests."""
import asyncio

import pytest


@pytest.mark.integration
class TestHealthChecks:
    def test_stac_api_health(self, stac_client):
        resp = stac_client.get("/")
        assert resp.status_code == 200

    def test_titiler_health(self, titiler_client):
        resp = titiler_client.get("/healthz")
        assert resp.status_code == 200

    def test_combined_health(self, stac_api_url, titiler_url):
        from eafw_stac.health import check_all_services

        result = asyncio.get_event_loop().run_until_complete(
            check_all_services(stac_api_url=stac_api_url, titiler_url=titiler_url)
        )
        assert "status" in result
        assert "services" in result
        assert len(result["services"]) >= 2
