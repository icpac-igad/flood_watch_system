"""Schema and mapping helpers for IBEW v2 shapefile ingestion.

These definitions are derived from the inspected shapefile schemas stored under
``reports/ibew_v2_schema_report.*`` and ``reports/ibew_v2_mapping.*``. They
describe how each downloaded IBEW v2 impact layer should be persisted into the
database models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Type

from django.contrib.gis.geos import (
    GEOSGeometry,
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
)

from Impact.models import (
    IBEWv2EconomicImpact,
    IBEWv2HealthImpact,
    IBEWv2HydrologicalData,
    IBEWv2InfrastructureImpact,
    IBEWv2PopulationImpact,
)


# Fields present in every polygon shapefile – mapped directly to BaseIBEWv2Model.
BASE_FIELD_MAP: Dict[str, str] = {
    "code_adm": "code_adm",
    "gid_0": "gid_0",
    "name_0": "name_0",
    "name_1": "name_1",
    "engtype_1": "engtype_1",
    "lack_cc": "lack_cc",
    "cod": "cod",
    "pop_tot": "pop_tot",
    "flood_tot": "flood_tot",
}


@dataclass(frozen=True)
class LayerConfig:
    """Static configuration describing how to ingest a shapefile layer."""

    slug: str
    model: Type
    category: str
    data_type: str
    geometry: str = "polygon"  # polygon | line
    return_period: Optional[int] = None
    return_period_attr: Optional[str] = None
    direct_field_map: Dict[str, str] = field(default_factory=dict)

    @property
    def expects_polygon(self) -> bool:
        return self.geometry == "polygon"

    @property
    def expects_line(self) -> bool:
        return self.geometry == "line"


# Mapping derived from reports/ibew_v2_mapping.txt
IBEW_V2_LAYER_SCHEMAS: Dict[str, LayerConfig] = {
    # Infrastructure
    "FPimpacts-built": LayerConfig(
        slug="FPimpacts-built",
        model=IBEWv2InfrastructureImpact,
        category="infrastructure",
        data_type="FPimpacts-built",
        direct_field_map={
            "tot_gov": "tot_gov",
            "tot_ind": "tot_ind",
            "tot_reslow": "tot_reslow",
            "tot_resmh": "tot_resmh",
            "tot_serv": "tot_serv",
        },
    ),
    "FPimpacts-services": LayerConfig(
        slug="FPimpacts-services",
        model=IBEWv2InfrastructureImpact,
        category="infrastructure",
        data_type="FPimpacts-services",
    ),
    # Economic
    "FPimpacts-cropland": LayerConfig(
        slug="FPimpacts-cropland",
        model=IBEWv2EconomicImpact,
        category="economic",
        data_type="FPimpacts-cropland",
    ),
    "FPimpacts-grazing": LayerConfig(
        slug="FPimpacts-grazing",
        model=IBEWv2EconomicImpact,
        category="economic",
        data_type="FPimpacts-grazing",
    ),
    "FPimpacts-livestock": LayerConfig(
        slug="FPimpacts-livestock",
        model=IBEWv2EconomicImpact,
        category="economic",
        data_type="FPimpacts-livestock",
    ),
    # Population
    "FPimpacts-displaced": LayerConfig(
        slug="FPimpacts-displaced",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-displaced",
        direct_field_map={
            "tot_crop": "tot_crop",
            "tot_graze": "tot_graze",
            "tot_ind": "tot_ind",
            "tot_res": "tot_res",
            "tot_serv": "tot_serv",
        },
    ),
    "FPimpacts-popaff25": LayerConfig(
        slug="FPimpacts-popaff25",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popaff25",
        return_period=25,
    ),
    "FPimpacts-popaff100": LayerConfig(
        slug="FPimpacts-popaff100",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popaff100",
        return_period=100,
    ),
    "FPimpacts-popafftot": LayerConfig(
        slug="FPimpacts-popafftot",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popafftot",
        direct_field_map={
            "tot_crop": "tot_crop",
            "tot_graze": "tot_graze",
            "tot_ind": "tot_ind",
            "tot_res": "tot_res",
            "tot_serv": "tot_serv",
            "flood_perc": "flood_perc",
            "flood_clas": "flood_clas",
        },
    ),
    "FPimpacts-popage25": LayerConfig(
        slug="FPimpacts-popage25",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popage25",
        return_period=25,
    ),
    "FPimpacts-popage100": LayerConfig(
        slug="FPimpacts-popage100",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popage100",
        return_period=100,
    ),
    "FPimpacts-popcens25": LayerConfig(
        slug="FPimpacts-popcens25",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popcens25",
        return_period=25,
    ),
    "FPimpacts-popcens100": LayerConfig(
        slug="FPimpacts-popcens100",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popcens100",
        return_period=100,
    ),
    "FPimpacts-popmob25": LayerConfig(
        slug="FPimpacts-popmob25",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popmob25",
        return_period=25,
    ),
    "FPimpacts-popmob100": LayerConfig(
        slug="FPimpacts-popmob100",
        model=IBEWv2PopulationImpact,
        category="population",
        data_type="FPimpacts-popmob100",
        return_period=100,
    ),
    # Health
    "FPimpacts-healthtot": LayerConfig(
        slug="FPimpacts-healthtot",
        model=IBEWv2HealthImpact,
        category="health",
        data_type="FPimpacts-healthtot",
    ),
    # Hydrology
    "returnPeriod": LayerConfig(
        slug="returnPeriod",
        model=IBEWv2HydrologicalData,
        category="hydrology",
        data_type="returnPeriod",
        geometry="line",
        return_period_attr="rp",
        direct_field_map={"log_ups": "log_ups"},
    ),
}


def normalise_geometry(geom: GEOSGeometry, expects_polygon: bool) -> GEOSGeometry:
    """Ensure geometries are stored as MultiPolygon or MultiLineString."""

    if isinstance(geom, GeometryCollection):  # type: ignore[isinstance]
        parts = [normalise_geometry(part, expects_polygon) for part in geom]
        if expects_polygon:
            polygons = []
            for part in parts:
                if isinstance(part, MultiPolygon):  # type: ignore[isinstance]
                    polygons.extend(list(part))
                elif isinstance(part, Polygon):  # type: ignore[isinstance]
                    polygons.append(part)
            if polygons:
                return MultiPolygon(polygons)
        else:
            lines = []
            for part in parts:
                if isinstance(part, MultiLineString):  # type: ignore[isinstance]
                    lines.extend(list(part))
                elif isinstance(part, LineString):  # type: ignore[isinstance]
                    lines.append(part)
            if lines:
                return MultiLineString(*lines) if len(lines) > 1 else MultiLineString(lines[0])

    if expects_polygon:
        if isinstance(geom, Polygon):  # type: ignore[isinstance]
            return MultiPolygon(geom)
        if isinstance(geom, MultiPolygon):  # type: ignore[isinstance]
            return geom
    else:
        if isinstance(geom, LineString):  # type: ignore[isinstance]
            return MultiLineString(geom)
        if isinstance(geom, MultiLineString):  # type: ignore[isinstance]
            return geom
    # Fallback: buffer(0) to sanitise and wrap
    return geom.buffer(0)


def extract_date_and_slug(shapefile_path: Path) -> tuple[str, str, str]:
    """Return (data_date, time_run, layer_slug) for a shapefile path."""

    stem = shapefile_path.stem
    parts = stem.split("_", 1)
    if len(parts) != 2 or len(parts[0]) != 12:
        raise ValueError(f"Unexpected shapefile naming pattern: {stem}")

    timestamp, slug = parts
    data_date = f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    time_run = timestamp[8:12]
    return data_date, time_run, slug


def resolve_config(layer_slug: str) -> LayerConfig:
    try:
        return IBEW_V2_LAYER_SCHEMAS[layer_slug]
    except KeyError as exc:
        raise KeyError(f"No LayerConfig registered for slug '{layer_slug}'") from exc
