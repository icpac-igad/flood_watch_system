import json

from django import template

from mapwidget.models import MapWidgetSettings

register = template.Library()


@register.filter(name="jsonify")
def jsonify(value):
    """Serialize a Python object to a JSON string safe for use in HTML attributes."""
    return json.dumps(value) if value is not None else "null"


@register.inclusion_tag("mapwidget/map_widget.html")
def render_map_widget():
    """Render the homepage map widget.

    All layer configs, basemap styles, and timestamps are fetched at runtime
    from the same API endpoints the mapviewer uses (/api/datasets/,
    /api/mapviewer-config).  The template tag only passes the widget settings
    (CTA text, logo, etc.) and the list of featured dataset entries.
    """
    mw = MapWidgetSettings.load()

    entries = []
    for entry in mw.map_datasets.order_by("sort_order"):
        entries.append(
            {
                "title": entry.title,
                "icon": entry.icon,
                "default_active": entry.default_active,
                "dataset_id": entry.dataset_id,
            }
        )

    return {
        "map_widget": mw,
        "dataset_entries": entries,
    }
