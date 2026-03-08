"""Security tests for STAC integration."""
import pytest

from eafw_stac.security import sanitize_id, validate_bbox, validate_datetime


class TestSanitizeID:
    def test_valid_id(self):
        assert sanitize_id("flood-extent-25y") == "flood-extent-25y"
        assert sanitize_id("asap_cropland") == "asap_cropland"
        assert sanitize_id("layer.v2") == "layer.v2"

    def test_invalid_id_special_chars(self):
        with pytest.raises(ValueError):
            sanitize_id("'; DROP TABLE collections;--")

    def test_invalid_id_empty(self):
        with pytest.raises(ValueError):
            sanitize_id("")

    def test_invalid_id_starts_with_special(self):
        with pytest.raises(ValueError):
            sanitize_id("-invalid-start")


class TestValidateBbox:
    def test_valid_ghoa_bbox(self):
        ok, msg = validate_bbox([21, -12, 52, 23])
        assert ok is True
        assert msg is None

    def test_valid_bbox_outside_ghoa_warns(self):
        ok, msg = validate_bbox([100, 10, 110, 20])
        assert ok is True
        assert "warning" in msg

    def test_invalid_bbox_wrong_length(self):
        ok, msg = validate_bbox([1, 2, 3])
        assert ok is False

    def test_invalid_bbox_south_greater_than_north(self):
        ok, msg = validate_bbox([21, 23, 52, -12])
        assert ok is False

    def test_invalid_bbox_out_of_range(self):
        ok, msg = validate_bbox([200, -12, 300, 23])
        assert ok is False


class TestValidateDatetime:
    def test_valid_single_datetime(self):
        ok, msg = validate_datetime("2024-01-01T00:00:00Z")
        assert ok is True

    def test_valid_interval(self):
        ok, msg = validate_datetime("2024-01-01T00:00:00Z/2024-12-31T23:59:59Z")
        assert ok is True

    def test_valid_open_interval(self):
        ok, msg = validate_datetime("2024-01-01T00:00:00Z/..")
        assert ok is True

    def test_invalid_both_open(self):
        ok, msg = validate_datetime("../..")
        assert ok is False

    def test_invalid_format(self):
        ok, msg = validate_datetime("not-a-date")
        assert ok is False

    def test_empty_string(self):
        ok, msg = validate_datetime("")
        assert ok is False


@pytest.mark.integration
class TestWriteProtection:
    def test_write_without_api_key_blocked(self, stac_api_url):
        """POST to STAC API via nginx without API key should be blocked."""
        import httpx

        base = stac_api_url.replace(":9070", ":9068")
        resp = httpx.post(
            f"{base}/stac/collections",
            json={"id": "test", "type": "Collection"},
            timeout=10,
        )
        # Nginx should block with 403
        assert resp.status_code in (403, 405, 422)
