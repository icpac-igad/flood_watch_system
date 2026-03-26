"""JSON utilities for extracting values from nested structures using path notation."""
import logging
import re

logger = logging.getLogger("geomanager.json_utils")

def normalize_json_path(json_path):
    """
    Normalize JSON path to dot notation.

    Supports multiple formats:
    - Dot notation: data.results.0.timestamp
    - Bracket notation: [data][results][0][timestamp]
    - JavaScript mixed: data.results[0].timestamp (most common)
    - Quoted keys: data['results'][0]["timestamp"]

    All formats are converted to: data.results.0.timestamp
    """
    if not json_path:
        return json_path

    # Pattern matches: [123] or ['key'] or ["key"] or [key]
    # Captures the key/index without quotes
    pattern = r'\[([\'"]?)([^\]]+?)\1\]'

    def replacer(match):
        quote = match.group(1)  # ' or " or empty
        key = match.group(2)    # the key/index
        return f'.{key}'

    # Replace all bracket notations with dot notation
    normalized = re.sub(pattern, replacer, json_path)

    # Remove leading dot if path started with bracket notation
    if normalized.startswith('.'):
        normalized = normalized[1:]

    return normalized


def _traverse_list(current, key):
    """Helper function to traverse a list in JSON data."""
    # Handle list indexing
    if key.isdigit():
        index = int(key)
        if 0 <= index < len(current):
            return current[index]
        return None
    else:
        # Non-numeric key on list - search for matching key in list items
        for item in current:
            if isinstance(item, dict) and key in item:
                return item[key]
        return None


def _traverse_dict(current, key):
    """Helper function to traverse a dictionary in JSON data."""
    return current.get(key)


def extract_value_by_path(data, json_path):
    """
    Extract value from nested JSON using dot notation path.
    Handles both dictionary keys and list indices.
    """
    if not json_path:
        return None

    # Normalize the path first
    normalized_path = normalize_json_path(json_path)
    keys = normalized_path.split('.')
    current = data

    for key in keys:
        if current is None:
            return None

        if isinstance(current, list):
            current = _traverse_list(current, key)
        elif isinstance(current, dict):
            current = _traverse_dict(current, key)
        else:
            return None

    return str(current) if current is not None else None


def extract_fields_from_data(data, field_names):
    """Extract multiple fields from a dictionary."""
    if not isinstance(data, dict):
        raise ValueError(f"Data must be a dictionary for field extraction, got {type(data)}")

    extracted = {}
    for field_name in field_names:
        value = data.get(field_name, "")
        extracted[field_name] = value

    return extracted
