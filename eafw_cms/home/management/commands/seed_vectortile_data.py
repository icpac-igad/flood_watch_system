"""
Management command to seed vector tile layer configuration data.

This ensures multimodal and boundary layers are properly configured
with their icons for MapLibre rendering.

Usage:
    python manage.py seed_vectortile_data
    python manage.py seed_vectortile_data --force  # Re-seed even if data exists
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Seed vector tile layer configuration data for MapLibre"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-seed even if data exists",
        )
        parser.add_argument(
            "--tileserv-url",
            type=str,
            default=None,
            help="pg_tileserv base URL (default: from TILESERV_BASE_URL env or http://localhost:7800)",
        )

    def handle(self, *args, **options):
        # Import here to avoid circular imports
        from geomanager.models import VectorTileLayer, VectorTileLayerIcon

        force = options["force"]
        tileserv_url = options["tileserv_url"] or os.environ.get(
            "TILESERV_BASE_URL", "http://localhost:7800"
        )

        self.stdout.write(f"Using pg_tileserv URL: {tileserv_url}")

        # Check if multimodal layer exists
        multimodal_id = "b5e354f2-46c8-4323-9814-71e3c435261b"
        multimodal_exists = VectorTileLayer.objects.filter(id=multimodal_id).exists()

        if multimodal_exists and not force:
            self.stdout.write(
                self.style.WARNING(
                    "Multimodal layer already exists. Use --force to re-seed."
                )
            )
        else:
            self._seed_multimodal_layer(VectorTileLayer, tileserv_url, multimodal_id)
            self._seed_multimodal_icons(VectorTileLayerIcon, multimodal_id)

        # Seed admin boundary layers
        self._seed_admin_layers(VectorTileLayer, tileserv_url, force)

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Layers: {VectorTileLayer.objects.count()}, "
                f"Icons: {VectorTileLayerIcon.objects.count()}"
            )
        )

    def _seed_multimodal_layer(self, VectorTileLayer, tileserv_url, layer_id):
        """Seed the Multi Model layer configuration."""
        layer, created = VectorTileLayer.objects.update_or_create(
            id=layer_id,
            defaults={
                "title": "Multi Model",
                "default": True,
                # Disable clustering by forcing cluster_zoom=0 so tiles always return individual points
                "base_url": f"{tileserv_url}/pg/tileserv/gha.multimodal_points_clustered/{{z}}/{{x}}/{{y}}.pbf?cluster_zoom=0",
                "query_params_static": [],
                "query_params_selectable": [],
                "params_selectors_side_by_side": False,
                "legend": [
                    {
                        "id": "legend-multimodal",
                        "type": "legend",
                        "value": {
                            "type": "basic",
                            "title": "Alert Level",
                            "items": [
                                {
                                    "icon": "/media/vector_tile_icons/emergency.png",
                                    "name": "Emergency (≥100)",
                                    "color": "#d32f2f",
                                },
                                {
                                    "icon": "/media/vector_tile_icons/alarm.png",
                                    "name": "Alarm (50-100)",
                                    "color": "#ff9800",
                                },
                                {
                                    "icon": "/media/vector_tile_icons/warning.png",
                                    "name": "Warning (10-50)",
                                    "color": "#ffc107",
                                },
                                {
                                    "icon": "/media/vector_tile_icons/normal.png",
                                    "name": "Normal (<10)",
                                    "color": "#9E9E9E",
                                },
                            ],
                        },
                    }
                ],
                "more_info": [],
                "render_layers": [],
                "get_time_from_tile_json": True,
                "tile_json_url": "/api/multimodal/dates/",
                "timestamps_response_object_key": "timestamps",
                "time_parameter_name": "date",
                "date_format": "yyyy-MM-dd",
                "render_layers_json": [
                    {
                        "id": "multimodal-circles",
                        "type": "circle",
                        "paint": {
                            "circle-radius": [
                                "interpolate",
                                ["linear"],
                                ["zoom"],
                                3, 4,
                                6, 5,
                                9, 7,
                                12, 9
                            ],
                            "circle-color": [
                                "match",
                                ["get", "alert_level"],
                                "emergency",
                                "#d32f2f",
                                "alarm",
                                "#ff9800",
                                "warning",
                                "#ffc107",
                                "normal",
                                "#4caf50",
                                "#4caf50"
                            ],
                            "circle-stroke-width": 1.5,
                            "circle-stroke-color": "#ffffff",
                            "circle-opacity": 0.9,
                        },
                        "metadata": {"position": "top"},
                        "source-layer": "gha.multimodal_points_clustered",
                    }
                ],
                "use_render_layers_json": True,
                "popup_config": [
                    {
                        "id": "mm-cluster-info",
                        "type": "popup_fields",
                        "value": {
                            "label": "Points in Cluster",
                            "data_key": "point_count",
                            "data_type": "number",
                        },
                    },
                    {
                        "id": "mm-cluster-max",
                        "type": "popup_fields",
                        "value": {
                            "label": "Max Discharge (m³/s)",
                            "data_key": "daily_max",
                            "data_type": "number",
                        },
                    },
                    {
                        "id": "mm-cluster-alert",
                        "type": "popup_fields",
                        "value": {
                            "label": "Highest Alert",
                            "data_key": "alert_level",
                            "data_type": "string",
                        },
                    },
                    {
                        "id": "mm-001",
                        "type": "popup_fields",
                        "value": {
                            "label": "Location",
                            "data_key": "admin_name",
                            "data_type": "string",
                        },
                    },
                    {
                        "id": "mm-002",
                        "type": "popup_fields",
                        "value": {
                            "label": "Point ID",
                            "data_key": "point_id",
                            "data_type": "number",
                        },
                    },
                    {
                        "id": "mm-003",
                        "type": "popup_fields",
                        "value": {
                            "label": "Forecast Date",
                            "data_key": "forecast_date",
                            "data_type": "string",
                        },
                    },
                    {
                        "id": "mm-004",
                        "type": "popup_fields",
                        "value": {
                            "label": "Daily Max (m³/s)",
                            "data_key": "daily_max",
                            "data_type": "number",
                        },
                    },
                    {
                        "id": "mm-005",
                        "type": "popup_fields",
                        "value": {
                            "label": "Daily Avg (m³/s)",
                            "data_key": "daily_avg",
                            "data_type": "number",
                        },
                    },
                    {
                        "id": "mm-006",
                        "type": "popup_fields",
                        "value": {
                            "label": "Forecasts",
                            "hidden": True,
                            "data_key": "forecasts_json",
                            "data_type": "string",
                        },
                    },
                ],
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Multi Model layer"))

    def _seed_multimodal_icons(self, VectorTileLayerIcon, layer_id):
        """Seed the icons for Multi Model layer."""
        icons = [
            {"name": "emergency", "color": "#B71C1C", "file": "vector_tile_icons/emergency.png"},
            {"name": "alarm", "color": "#FF5722", "file": "vector_tile_icons/alarm.png"},
            {"name": "warning", "color": "#FFA726", "file": "vector_tile_icons/warning.png"},
            {"name": "normal", "color": "#9E9E9E", "file": "vector_tile_icons/normal.png"},
        ]

        for icon_data in icons:
            icon, created = VectorTileLayerIcon.objects.update_or_create(
                name=icon_data["name"],
                layer_id=layer_id,
                defaults={
                    "color": icon_data["color"],
                    "file": icon_data["file"],
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} icon: {icon_data['name']}")

    def _seed_admin_layers(self, VectorTileLayer, tileserv_url, force):
        """Seed admin boundary layers."""
        admin_layers = [
            {
                "id": "b6c3b7d9-c3dd-4012-9cc9-857f0640e702",
                "title": "Admin Level 0 Boundary",
                "source_layer": "gha.admin0",
                "line_width": 1.2,
                "line_opacity": 1.0,
                "order": 0,
            },
            {
                "id": "02453614-2716-4ca3-bc82-589b364fe47e",
                "title": "Admin Level 1 Boundary",
                "source_layer": "gha.admin1",
                "line_width": 0.8,
                "line_opacity": 0.6,
                "order": 1,
            },
        ]

        for layer_data in admin_layers:
            exists = VectorTileLayer.objects.filter(id=layer_data["id"]).exists()
            if exists and not force:
                self.stdout.write(f"  {layer_data['title']} exists, skipping")
                continue

            layer, created = VectorTileLayer.objects.update_or_create(
                id=layer_data["id"],
                defaults={
                    "title": layer_data["title"],
                    "default": True,
                    "base_url": f"{tileserv_url}/pg/tileserv/{layer_data['source_layer']}/{{z}}/{{x}}/{{y}}.pbf",
                    "order": layer_data["order"],
                    "query_params_static": [],
                    "query_params_selectable": [],
                    "legend": [],
                    "more_info": [
                        {
                            "id": "info-gadm",
                            "type": "more_info",
                            "value": {
                                "text": "Political boundaries data obtained from GADM.",
                                "link_url": "https://gadm.org/",
                                "is_button": True,
                                "link_text": "Read More",
                                "show_arrow": True,
                            },
                        }
                    ],
                    "render_layers": [
                        {
                            "id": f"fill-{layer_data['id'][:8]}",
                            "type": "fill",
                            "value": {
                                "paint": {
                                    "fill_color": "#ffffff",
                                    "fill_opacity": 0.1,
                                    "fill_antialias": True,
                                    "fill_outline_color": "#000000",
                                },
                                "source_layer": layer_data["source_layer"],
                            },
                        },
                        {
                            "id": f"line-{layer_data['id'][:8]}",
                            "type": "line",
                            "value": {
                                "paint": {
                                    "line_color": "#000000",
                                    "line_width": layer_data["line_width"],
                                    "line_opacity": layer_data["line_opacity"],
                                },
                                "layout": {
                                    "line_cap": "butt",
                                    "line_join": "miter",
                                },
                                "source_layer": layer_data["source_layer"],
                            },
                        },
                    ],
                    "get_time_from_tile_json": False,
                    "use_render_layers_json": False,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {action} {layer_data['title']}"))
