import json
import math
from urllib.parse import urljoin, urlsplit
from uuid import UUID

from django.conf import settings
from django.utils.translation import gettext_lazy as _


def get_full_url(request, path):
    """Compat shim — wagtail.api.v2.utils.get_full_url removed in Wagtail 7.

    Prefers the request's host so URLs match the caller's origin (avoids
    CORS issues when CMS_BASE_URL points to a different IP/host).
    Falls back to CMS_BASE_URL only when there is no request context.
    """
    if not path:
        path = ""

    if isinstance(path, str) and request and path.startswith(("http://", "https://")):
        # If an internal app URL was stored as an absolute URL with another host,
        # normalize it to the active request host to avoid cross-origin tile/API calls.
        parsed = urlsplit(path)
        if parsed.path.startswith(
            (
                "/api/",
                "/pg/",
                "/tileserv/",
                "/mapcache/",
                "/mapserver/",
                "/cog-tiles/",
                "/media/",
                "/static/",
                "/stac-browser/api/",
            )
        ):
            path = f"{parsed.path}{f'?{parsed.query}' if parsed.query else ''}{f'#{parsed.fragment}' if parsed.fragment else ''}"

    if request:
        return request.build_absolute_uri(path)
    cms_base_url = getattr(settings, "CMS_BASE_URL", None)
    if cms_base_url:
        if path and not path.startswith("/"):
            path = "/" + path
        return urljoin(cms_base_url, path)
    return path


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def significant_digits(step, number):
    """
    This function calculates the number of significant digits to keep after the decimal
    point based on a given step value.

    Args:
        step: The minimum absolute difference between two values considered significant.
        number: The number to analyze.


    Returns:
        The number of significant digits to keep.
    """
    if number == 0:
        return 1  # Handle zero case

    # Convert the number to absolute value and handle negatives
    abs_number = abs(number)
    # Get the integer part (number of leading zeros not considered significant)
    exponent = int(math.floor(math.log10(abs_number)))

    # If the number is less than 1 (between 0 and 1), consider the leading zero
    if abs_number < 1:
        exponent -= 1

    # Calculate significant digits based on exponent and step
    sign_digits = max(0, exponent + 1)  # At least 1 significant digit
    if step > 0:
        sign_digits = max(sign_digits, int(math.ceil(math.log10(abs_number) / math.log10(step))))

    return sign_digits


def round_to_precision(precision=None):
    """
    This function creates and returns another function that rounds numbers to a specified precision.

    Args:
        precision: The desired number of decimal places for rounding (optional).

    Returns:
        A function that rounds numbers to the specified precision.
    """
    if precision is None:

        def inner(n):
            return n  # No rounding if precision is not specified

        return inner

    multiplier = 10**precision

    def inner(n):
        """
        Inner function that performs rounding based on the multiplier.
        """
        return round(n * multiplier) / multiplier

    return inner
