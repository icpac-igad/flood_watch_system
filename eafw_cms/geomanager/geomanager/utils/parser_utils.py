"""
Date parsing utilities for extracting and transforming dates from various formats and structures.
"""

import logging
import string
import json
from datetime import datetime
from geomanager.utils.constants import JS_TO_PYTHONIC_DATE_FORMAT_CHOICES
from geomanager.utils.json_utils import extract_value_by_path

logger = logging.getLogger("geomanager.parser_utils")

FALLBACK_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601: 2025-10-11T18:00:00+00:00
    "%Y-%m-%dT%H:%M:%S",  # ISO 8601 no TZ: 2025-10-11T18:00:00
    "%Y-%m-%d %H:%M:%S",  # 2025-10-11 18:00:00
    "%Y-%m-%d %H:%M",  # 2025-10-11 18:00
    "%Y-%m-%d",  # 2025-10-11
    "%Y-%m",
    "%Y",
]


class TransformationRegistry:
    """Registry for field value transformations."""

    _transformations = {}

    @classmethod
    def register(cls, name, func):
        """Register a transformation function."""
        cls._transformations[name] = func

    @classmethod
    def apply(cls, value, transformation):
        # Apply transformation to a field value
        # Check for direct transformation match
        if transformation in cls._transformations:
            return cls._transformations[transformation](value)

        # Handle parametrized transformations (e.g., "zfill:2")
        if ":" in transformation:
            trans_type, param = transformation.split(":", 1)
            if trans_type in cls._transformations:
                return cls._transformations[trans_type](value, param)

        # Handle custom map transformations (e.g., "map:{...}")
        if transformation.startswith("map:"):
            mapping = json.loads(transformation[4:])
            return mapping.get(str(value), str(value))

        logger.warning(f"Unknown transformation type: {transformation}")
        return value


# Register built-in transformations
TransformationRegistry.register("zfill", lambda v, digits: str(v).zfill(int(digits)))


def parse_date_string(date_string, date_format=None):
    """
    Parse date string using specified format or default format.
    Args:
        date_string: The date string to parse
        date_format: Optional format specifier from DATE_FORMAT_CHOICES
    Returns:
        datetime object
    """
    if not date_string:
        raise ValueError("Date string is empty or None")

    # Get Python date format from JS format
    if date_format and date_format in JS_TO_PYTHONIC_DATE_FORMAT_CHOICES:
        python_format = JS_TO_PYTHONIC_DATE_FORMAT_CHOICES[date_format]
    else:
        # Default to standard date format
        python_format = "%Y-%m-%d"

    try:
        return datetime.strptime(date_string, python_format)
    except ValueError:
        # Try fallback formats
        for fmt in FALLBACK_DATE_FORMATS:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue

        raise ValueError(f"Could not parse date '{date_string}' with any known format")


# ============================================================================
# Date Extraction Strategies
# ============================================================================


class DateExtractionStrategy:
    """Base class for date extraction strategies."""

    def extract_date_string(self, data, config):
        """Extract date string from data using configuration."""
        raise NotImplementedError

    def get_date_format(self, config):
        """Get the date format from configuration."""
        return config.get("date_format", "yyyy-MM-dd")


class DirectDateFieldExtractor(DateExtractionStrategy):
    """Extract date directly from a single field using JSON path."""

    def extract_date_string(self, data, config):
        """Extract date value from JSON data using JSON path."""
        json_path = config.get("json_path")
        if not json_path:
            raise ValueError("No json_path specified in configuration")

        date_string = extract_value_by_path(data, json_path)

        if not date_string:
            raise ValueError(f"No value found at path '{json_path}'. Check API response structure.")

        return date_string


class MultiFieldDateConstructor(DateExtractionStrategy):
    """Construct date from multiple fields using template and mappings."""

    def extract_date_string(self, data, config):
        """Construct date string from multiple fields using template and mappings."""
        template = config.get("template")
        field_mappings = config.get("field_mappings", {})
        transformations = config.get("transformations", {})

        if not template:
            raise ValueError("No template specified in configuration")

        # Extract template variables
        formatter = string.Formatter()
        template_vars = [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]

        context = {}

        for var in template_vars:
            # Get field name from mapping
            field_name = field_mappings.get(var, var)

            # Extract value from data
            if isinstance(data, dict):
                field_value = data.get(field_name, "")
            else:
                raise ValueError(f"Data must be a dictionary for field extraction, got {type(data)}")

            # Apply transformations
            if var in transformations:
                field_value = TransformationRegistry.apply(field_value, transformations[var])

            # Convert to appropriate type
            try:
                context[var] = int(field_value)
            except (ValueError, TypeError):
                context[var] = field_value

        # Format template with extracted values
        try:
            return template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing field {e} in data for template '{template}'")

    def get_date_format(self, config):
        """Multi-field constructor always produces YYYY-MM-DD format."""
        return "yyyy-MM-dd"


class UniversalDateParser:
    """Universal parser that handles all date extraction scenarios."""

    @staticmethod
    def _get_strategy(config):
        """Determine the appropriate extraction strategy based on config."""
        if "template" in config:
            return MultiFieldDateConstructor()
        else:
            return DirectDateFieldExtractor()

    @staticmethod
    def parse(data, config):
        """
        Parse date from data using configuration
        """
        try:
            # Get the appropriate strategy
            strategy = UniversalDateParser._get_strategy(config)

            # Extract date string
            date_string = strategy.extract_date_string(data, config)

            # Get date format
            date_format = strategy.get_date_format(config)

            # Parse date string
            return parse_date_string(date_string, date_format)

        except Exception as e:
            logger.error(f"Date parsing failed: {str(e)} | Config: {config}")
            raise Exception(f"Universal date parsing failed: {str(e)}")


def universal_date_parser(data, config):
    """
    Parse date from data - convenience function.

    Deprecated: Use UniversalDateParser.parse() instead.
    """
    return UniversalDateParser.parse(data, config)
