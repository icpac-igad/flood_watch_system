from django.core.management.base import BaseCommand
from django.db import transaction

from geomanager.models import (
    Category,
    Dataset,
    Metadata,
    SubCategory,
    WmsLayer,
    WmsRequestLayer,
)


REQUIRED_SUBCATEGORIES = (
    "Exposure",
    "Flood Extent / Hazard",
)

REQUIRED_EXPOSURE_DATASETS = (
    "Population",
    "Buildings",
    "Roads",
    "Cropland",
    "Hospitals",
    "Health Facilities",
)

FLOOD_DATASET_TITLE = "Flood extent/Hazard"
RETURN_PERIOD_LEGEND = [
    {
        "type": "legend",
        "value": {
            "type": "basic",
            "items": [
                {"value": "Low consensus (1/6)", "color": "#DEEBF7"},
                {"value": "Consensus (2/6)", "color": "#C6DBEF"},
                {"value": "Consensus (3/6)", "color": "#9ECAE1"},
                {"value": "Consensus (4/6)", "color": "#6BAED6"},
                {"value": "High consensus (5/6)", "color": "#3182BD"},
                {"value": "Very high consensus (6/6)", "color": "#08519C"},
            ],
        },
    }
]


class Command(BaseCommand):
    help = (
        "Configure Impact category for flood extent/hazard as WMS multi-layer (25y/100y), "
        "keep required subcategories/datasets, and refresh metadata."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--map-base-url",
            default="/cog-tiles/",
            help="Base tile URL used by Flood extent/Hazard layers (default: /cog-tiles/)",
        )
        parser.add_argument(
            "--keep-only-required",
            action="store_true",
            default=False,
            help="Delete Impact datasets not in the required list.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show planned actions without writing to the database.",
        )

    def handle(self, *args, **options):
        map_base_url = options["map_base_url"]
        keep_only_required = options["keep_only_required"]
        dry_run = options["dry_run"]

        removed_datasets = []

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode; no DB writes will be applied."))

        with transaction.atomic():
            impact = Category.objects.filter(title__icontains="impact").first()
            if not impact:
                if dry_run:
                    self.stdout.write("Would create Impact category.")
                    return
                impact = Category.objects.create(title="Impact", icon="", active=True, public=True)
                self.stdout.write(self.style.SUCCESS("Created Impact category."))

            if not impact.active or not impact.public:
                if dry_run:
                    self.stdout.write("Would set Impact category active/public.")
                else:
                    impact.active = True
                    impact.public = True
                    impact.save(update_fields=["active", "public", "modified"])

            subcats = {}
            for title in REQUIRED_SUBCATEGORIES:
                subcat = SubCategory.objects.filter(category=impact, title__iexact=title).first()

                if not subcat:
                    if dry_run:
                        self.stdout.write(f"Would create subcategory '{title}'.")
                        continue
                    subcat = SubCategory.objects.create(
                        category=impact,
                        title=title,
                        active=True,
                        public=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created subcategory '{title}'."))
                else:
                    changed = False
                    if not subcat.active:
                        subcat.active = True
                        changed = True
                    if not subcat.public:
                        subcat.public = True
                        changed = True
                    if changed and not dry_run:
                        subcat.save(update_fields=["active", "public"])

                subcats[title] = subcat

            allowed_titles = set(REQUIRED_EXPOSURE_DATASETS + (FLOOD_DATASET_TITLE,))
            if keep_only_required:
                for ds in Dataset.objects.filter(category=impact):
                    if ds.title not in allowed_titles:
                        removed_datasets.append(ds.title)
                        if dry_run:
                            self.stdout.write(f"Would delete extra Impact dataset '{ds.title}'.")
                        else:
                            ds.delete()

            for title in REQUIRED_EXPOSURE_DATASETS:
                ds = Dataset.objects.filter(title__iexact=title).first()

                if not ds:
                    if dry_run:
                        self.stdout.write(f"Would create Exposure dataset '{title}'.")
                        continue
                    ds = Dataset.objects.create(
                        title=title,
                        category=impact,
                        sub_category=subcats["Exposure"],
                        dataset_slug=title.lower().replace(" ", "-"),
                        layer_type="wms" if title == "Population" else "raster_file",
                        published=True,
                        public=True,
                        multi_temporal=False,
                        multi_layer=False,
                        initial_visible=False,
                        current_time_method="latest_from_source",
                        can_clip=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created Exposure dataset '{title}'."))
                else:
                    changed = False
                    if ds.category_id != impact.id:
                        ds.category = impact
                        changed = True
                    if ds.sub_category_id != subcats["Exposure"].id:
                        ds.sub_category = subcats["Exposure"]
                        changed = True
                    expected_slug = title.lower().replace(" ", "-")
                    if ds.dataset_slug != expected_slug:
                        ds.dataset_slug = expected_slug
                        changed = True
                    if not ds.published:
                        ds.published = True
                        changed = True
                    if not ds.public:
                        ds.public = True
                        changed = True
                    if changed and not dry_run:
                        ds.save()

            flood_ds = Dataset.objects.filter(title__iexact=FLOOD_DATASET_TITLE).first()
            if not flood_ds:
                if dry_run:
                    self.stdout.write("Would create Flood extent/Hazard dataset.")
                    return
                flood_ds = Dataset.objects.create(
                    title=FLOOD_DATASET_TITLE,
                    category=impact,
                    sub_category=subcats["Flood Extent / Hazard"],
                    layer_type="wms",
                    dataset_slug="flood-extent-hazard",
                    summary="Fluvial flood hazard model-consensus for 25-year and 100-year return periods",
                    published=True,
                    public=True,
                    initial_visible=False,
                    multi_temporal=False,
                    multi_layer=True,
                    enable_all_multi_layers_on_add=False,
                    current_time_method="latest_from_source",
                    can_clip=False,
                )
                self.stdout.write(self.style.SUCCESS("Created Flood extent/Hazard dataset."))

            flood_ds.category = impact
            flood_ds.sub_category = subcats["Flood Extent / Hazard"]
            flood_ds.layer_type = "wms"
            flood_ds.dataset_slug = "flood-extent-hazard"
            flood_ds.summary = "Fluvial flood hazard model-consensus for 25-year and 100-year return periods"
            flood_ds.published = True
            flood_ds.public = True
            flood_ds.initial_visible = False
            flood_ds.multi_temporal = False
            flood_ds.multi_layer = True
            flood_ds.enable_all_multi_layers_on_add = False
            flood_ds.current_time_method = "latest_from_source"
            flood_ds.can_clip = False

            if dry_run:
                self.stdout.write("Would update Flood extent/Hazard dataset core fields.")
            else:
                flood_ds.save()

            if dry_run:
                if flood_ds.raster_file_layers.exists():
                    self.stdout.write(
                        f"Would delete {flood_ds.raster_file_layers.count()} Flood raster-file layer(s)."
                    )
            else:
                flood_ds.raster_file_layers.all().delete()

            metadata = flood_ds.metadata
            if not metadata:
                if dry_run:
                    self.stdout.write("Would create metadata for Flood extent/Hazard dataset.")
                else:
                    metadata = Metadata.objects.create(
                        title="Aggregated Fluvial Flood Hazard Outputs for Africa"
                    )
                    flood_ds.metadata = metadata
                    flood_ds.save(update_fields=["metadata", "modified"])

            if metadata and not dry_run:
                metadata.title = "Aggregated Fluvial Flood Hazard Outputs for Africa"
                metadata.subtitle = "Global Flood Partnership model-consensus hazard (return periods)"
                metadata.function = (
                    "Model-consensus fluvial flood hazard indicator for screening, "
                    "uncertainty assessment, and planning."
                )
                metadata.resolution = None
                metadata.geographic_coverage = "Africa"
                metadata.source = "Global Flood Partnership / Global Flood Model Intercomparison Project"
                metadata.license = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
                metadata.frequency_of_update = "Static (scenario-based return periods)"
                metadata.overview = (
                    "<p>Aggregated fluvial flood hazard outputs for Africa derived from six global flood models. "
                    "Pixel values represent inter-model inundation agreement (0-6), where higher values indicate "
                    "stronger consensus.</p>"
                    "<p>Available return periods in this deployment: 1-in-25 years and 1-in-100 years.</p>"
                    "<p>Data characteristics: WGS84, ~1/1200 degree (~90 m), single-band integer GeoTIFF.</p>"
                )
                metadata.cautions = (
                    "<p>This is a model-consensus hazard layer, not observed inundation depth. "
                    "Use with local context and exposure/vulnerability layers.</p>"
                )
                metadata.citation = (
                    "<p>Trigg, M.A., Bates, P.D., Neal, J.C. et al. (2016). "
                    "The credibility challenge for global fluvial flood risk analysis. "
                    "Environmental Research Letters.</p>"
                )
                metadata.learn_more = "https://doi.org/10.1088/1748-9326/11/1/014002"
                metadata.save()

            desired_layers = (
                ("25-year return period", "flood_extent_rp25", True, 0),
                ("100-year return period", "flood_extent_rp100", False, 1),
            )

            keep_wms_ids = []
            for title, request_layer_name, is_default, order in desired_layers:
                if dry_run:
                    self.stdout.write(
                        f"Would upsert WMS layer '{title}' -> '{request_layer_name}' using base URL '{map_base_url}'."
                    )
                    continue

                layer = flood_ds.wms_layers.filter(title__iexact=title).first()
                if not layer:
                    layer = WmsLayer.objects.create(
                        dataset=flood_ds,
                        title=title,
                        default=is_default,
                        base_url=map_base_url,
                        version="1.1.1",
                        width=256,
                        height=256,
                        transparent=True,
                        srs="EPSG:3857",
                        format="image/png",
                        request_time_from_capabilities=False,
                        can_clip=False,
                        order=order,
                        legend=RETURN_PERIOD_LEGEND,
                    )
                else:
                    layer.title = title
                    layer.default = is_default
                    layer.base_url = map_base_url
                    layer.version = "1.1.1"
                    layer.width = 256
                    layer.height = 256
                    layer.transparent = True
                    layer.srs = "EPSG:3857"
                    layer.format = "image/png"
                    layer.request_time_from_capabilities = False
                    layer.can_clip = False
                    layer.order = order
                    layer.legend = RETURN_PERIOD_LEGEND
                    layer.save()

                req = layer.wms_request_layers.first()
                if not req:
                    WmsRequestLayer.objects.create(
                        layer=layer,
                        name=request_layer_name,
                        sort_order=0,
                    )
                else:
                    req.name = request_layer_name
                    req.sort_order = 0
                    req.save(update_fields=["name", "sort_order"])
                    layer.wms_request_layers.exclude(pk=req.pk).delete()

                keep_wms_ids.append(layer.pk)

            if not dry_run:
                flood_ds.wms_layers.exclude(pk__in=keep_wms_ids).delete()

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run complete. Changes rolled back."))
                return

        self.stdout.write(self.style.SUCCESS("Impact flood WMS configuration completed."))
        if keep_only_required:
            self.stdout.write(f"Removed extra Impact datasets: {removed_datasets}")
