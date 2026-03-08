"""Pytest fixtures for STAC integration tests."""
import os

import httpx
import pytest


@pytest.fixture
def stac_api_url():
    return os.getenv("STAC_API_URL", "http://localhost:9070")


@pytest.fixture
def titiler_url():
    return os.getenv("TITILER_URL", "http://localhost:9071")


@pytest.fixture
def stac_browser_url():
    return os.getenv("STAC_BROWSER_URL", "http://localhost:9072")


@pytest.fixture
def stac_api_key():
    return os.getenv("STAC_API_KEY", "")


@pytest.fixture
def stac_client(stac_api_url):
    with httpx.Client(base_url=stac_api_url, timeout=30) as client:
        yield client


@pytest.fixture
def titiler_client(titiler_url):
    with httpx.Client(base_url=titiler_url, timeout=30) as client:
        yield client


# GHoA bounding box for search tests
GHOA_BBOX = [21, -12, 52, 23]
