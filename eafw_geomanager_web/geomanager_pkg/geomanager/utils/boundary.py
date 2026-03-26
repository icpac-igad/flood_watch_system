from urllib.parse import urlsplit, urlunsplit


def _tileserv_base_url(tiles_url):
    parsed = urlsplit(tiles_url or "")
    path = parsed.path or str(tiles_url or "")

    if "/pg/tileserv" in path:
        base_path = path.split("/pg/tileserv", 1)[0] + "/pg/tileserv"
        return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))

    if "/api/admin-boundary/tiles" in path or "/api/adm0-boundary/tiles" in path:
        prefix = path.split("/api/", 1)[0]
        return urlunsplit((parsed.scheme, parsed.netloc, f"{prefix}/pg/tileserv", "", ""))

    return urlunsplit((parsed.scheme, parsed.netloc, "/pg/tileserv", "", ""))


def _build_tileserv_tiles_url(base_url, collection_id):
    return f"{base_url}/{collection_id}" + "/{z}/{x}/{y}.pbf"


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
                "column": "name_1",
                "property": "Region",
                "type": "string",
            }
        )

    if level >= 2:
        base_output.append(
            {
                "column": "name_2",
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
    tileserv_base_url = _tileserv_base_url(tiles_url)
    return [
        _build_boundary_dataset(
            "political-boundaries",
            "political-boundaries",
            "Country Boundaries",
            "GHoA country boundaries",
            _build_tileserv_tiles_url(tileserv_base_url, "gha.admin0"),
            "gha.admin0",
            0,
            default=True,
        ),
        _build_boundary_dataset(
            "political-boundaries-admin1",
            "political-boundaries-admin1",
            "Region Boundaries",
            "GHoA region boundaries",
            _build_tileserv_tiles_url(tileserv_base_url, "gha.admin1"),
            "gha.admin1",
            1,
        ),
        _build_boundary_dataset(
            "political-boundaries-admin2",
            "political-boundaries-admin2",
            "District Boundaries",
            "GHoA district boundaries",
            _build_tileserv_tiles_url(tileserv_base_url, "gha.admin2"),
            "gha.admin2",
            2,
        ),
    ]
