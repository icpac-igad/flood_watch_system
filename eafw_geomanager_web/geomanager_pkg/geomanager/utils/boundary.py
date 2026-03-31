from urllib.parse import urlsplit, urlunsplit


def _api_base_url(tiles_url):
    """Derive the site prefix from any known tile URL pattern."""
    parsed = urlsplit(tiles_url or "")
    path = parsed.path or str(tiles_url or "")

    for marker in ("/pg/tileserv", "/api/admin-boundary/tiles", "/api/adm0-boundary/tiles"):
        if marker in path:
            prefix = path.split(marker, 1)[0]
            return urlunsplit((parsed.scheme, parsed.netloc, prefix, "", ""))

    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _build_boundary_tiles_url(base_url, admin_level):
    """Build URL pointing to the Django admin-boundary endpoint with a fixed admin_level.

    This endpoint understands scope=whca and other filter params, unlike raw
    pg_tileserv which ignores unknown query parameters.
    """
    return f"{base_url}/api/admin-boundary/tiles/{{z}}/{{x}}/{{y}}?admin_level={admin_level}"


def _boundary_render_layers(source_layer, level):
    level_styles = {
        0: {"line-color": "#2f2f2f", "line-width": 1.4, "line-opacity": 0.9},
        1: {"line-color": "#5b5b5b", "line-width": 1.0, "line-opacity": 0.85},
        2: {"line-color": "#767676", "line-width": 0.8, "line-opacity": 0.8},
    }
    line_style = level_styles[level]
    return [
        {
            "paint": {
                "fill-color": "#ffffff",
                "fill-opacity": 0,
            },
            "source-layer": source_layer,
            "type": "fill",
        },
        {
            "paint": line_style,
            "source-layer": source_layer,
            "type": "line",
        },
    ]


def _boundary_interaction_output(level):
    base_output = [
        {
            "column": "country",
            "property": "Country",
            "type": "string",
        }
    ]

    if level >= 1:
        base_output.append(
            {
                "column": "region",
                "property": "Region",
                "type": "string",
            }
        )

    if level >= 2:
        base_output.append(
            {
                "column": "district",
                "property": "Sub Region",
                "type": "string",
            }
        )

    return base_output


def _build_boundary_dataset(
    dataset_id,
    layer_id,
    name,
    description,
    tiles_url,
    source_layer,
    level,
    default=False,
):

    return {
        "id": dataset_id,
        "dataset": dataset_id,
        "name": name,
        "layer": layer_id,
        "isBoundary": True,
        "public": True,
        "layers": [
            {
                "id": layer_id,
                "isBoundary": True,
                "analysisEndpoint": "admin",
                "name": name,
                "default": default,
                "description": description,
                "layerConfig": {
                    "type": "vector",
                    "source": {
                        "type": "vector",
                        "tiles": [tiles_url],
                    },
                    "render": {
                        "layers": _boundary_render_layers(source_layer, level),
                    },
                },
                "interactionConfig": {
                    "output": _boundary_interaction_output(level),
                    "type": "intersection",
                },
            }
        ],
    }


def create_boundary_dataset(tiles_url):
    base_url = _api_base_url(tiles_url)
    # Use the Django admin-boundary endpoint which understands scope=whca and
    # other filter params.  Raw pg_tileserv table URLs ignore those params,
    # so the WHCA project filter had no effect on boundary layers.
    # The source-layer in the MVT is always "gha.admin_clipped".
    source_layer = "gha.admin_clipped"
    return [
        _build_boundary_dataset(
            "political-boundaries",
            "political-boundaries",
            "Country Boundaries",
            "GHoA country boundaries",
            _build_boundary_tiles_url(base_url, 0),
            source_layer,
            0,
            default=True,
        ),
        _build_boundary_dataset(
            "political-boundaries-admin1",
            "political-boundaries-admin1",
            "Region Boundaries",
            "GHoA region boundaries",
            _build_boundary_tiles_url(base_url, 1),
            source_layer,
            1,
        ),
        _build_boundary_dataset(
            "political-boundaries-admin2",
            "political-boundaries-admin2",
            "District Boundaries",
            "GHoA district boundaries",
            _build_boundary_tiles_url(base_url, 2),
            source_layer,
            2,
        ),
    ]
