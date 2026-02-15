import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geomanager.models import Category, Dataset, RasterFileLayer, SubCategory
from geomanager.settings import geomanager_settings
from geomanager.utils.ingest import ingest_raster_file

logger = logging.getLogger(__name__)

REQUIRED_IMPACT_SUBCATEGORIES = (
    "Exposure",
    "Susceptibility",
    "Vulnerability",
    "Resilience",
)

SUPPORTED_RASTER_EXTENSIONS = {".tif", ".nc"}


def _value(entry, *keys, default=None):
    for key in keys:
        if key in entry and entry[key] is not None:
            return entry[key]
    return default


class Command(BaseCommand):
    help = (
        "Bootstrap Impact flood raster datasets/layers from a JSON manifest and optionally ingest files "
        "from GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "manifest",
            type=str,
            help=(
                "Path to JSON manifest list. Each item must include: title, dataset_slug, "
                "sub_category, auto_ingest_directory"
            ),
        )
        parser.add_argument(
            "--ingest",
            action="store_true",
            default=False,
            help="Ingest matching .tif/.nc files from each layer directory after registration",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Overwrite existing LayerRasterFile rows during ingestion",
        )
        parser.add_argument(
            "--clip",
            action="store_true",
            default=False,
            help="Clip rasters to configured admin boundaries during ingestion",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Validate and print planned changes without writing to the database",
        )

    def handle(self, *args, **options):
        manifest_path = Path(options["manifest"]).expanduser().resolve()
        ingest = options["ingest"]
        overwrite = options["overwrite"]
        clip = options["clip"]
        dry_run = options["dry_run"]

        entries = self._load_manifest(manifest_path)

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode. No database writes will be made."))

        impact_category = self._ensure_impact_category(dry_run=dry_run)
        subcategories = self._ensure_required_subcategories(impact_category, dry_run=dry_run)

        ingest_targets = []

        for index, entry in enumerate(entries, start=1):
            dataset_slug = _value(entry, "dataset_slug", "slug")
            dataset_title = _value(entry, "title", "dataset_title")
            subcategory_name = _value(entry, "sub_category", "subcategory")
            directory_name = _value(
                entry,
                "auto_ingest_directory",
                "directory_name",
                "directory",
            )

            if not dataset_title:
                raise CommandError(f"Manifest item {index}: missing 'title'.")
            if not dataset_slug:
                raise CommandError(f"Manifest item {index}: missing 'dataset_slug'.")
            if not subcategory_name:
                raise CommandError(f"Manifest item {index}: missing 'sub_category'.")
            if not directory_name:
                raise CommandError(f"Manifest item {index}: missing 'auto_ingest_directory'.")

            normalized_subcat = self._normalize_subcategory_name(subcategory_name)
            if normalized_subcat not in subcategories:
                expected = ", ".join(REQUIRED_IMPACT_SUBCATEGORIES)
                raise CommandError(
                    f"Manifest item {index}: sub_category '{subcategory_name}' is invalid. Expected one of: {expected}."
                )

            subcategory = subcategories[normalized_subcat]

            layer_title = _value(entry, "layer_title", default=dataset_title)
            summary = _value(entry, "summary", default="")
            date_format = _value(entry, "date_format", default="yyyy-MM-dd HH:mm")
            time_parameter = _value(entry, "time_parameter", default="time")
            time_prefix = _value(entry, "time_prefix", default="")

            published = bool(_value(entry, "published", default=True))
            public = bool(_value(entry, "public", default=True))
            can_clip = bool(_value(entry, "can_clip", default=True))
            multi_temporal = bool(_value(entry, "multi_temporal", default=True))
            initial_visible = bool(_value(entry, "initial_visible", default=False))
            current_time_method = _value(entry, "current_time_method", default="latest_from_source")

            with transaction.atomic():
                dataset = self._upsert_dataset(
                    impact_category=impact_category,
                    subcategory=subcategory,
                    title=dataset_title,
                    slug=dataset_slug,
                    summary=summary,
                    published=published,
                    public=public,
                    can_clip=can_clip,
                    multi_temporal=multi_temporal,
                    initial_visible=initial_visible,
                    time_parameter=time_parameter,
                    time_prefix=time_prefix,
                    current_time_method=current_time_method,
                    dry_run=dry_run,
                )

                layer = self._upsert_layer(
                    dataset=dataset,
                    title=layer_title,
                    date_format=date_format,
                    directory_name=directory_name,
                    dry_run=dry_run,
                )

            ingest_targets.append((dataset_slug, directory_name, layer.id if layer else None))

        self.stdout.write(self.style.SUCCESS(f"Processed {len(entries)} manifest entries."))

        if ingest:
            self._run_ingest(ingest_targets, overwrite=overwrite, clip=clip, dry_run=dry_run)

    def _load_manifest(self, manifest_path: Path):
        if not manifest_path.exists():
            raise CommandError(f"Manifest file does not exist: {manifest_path}")

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON manifest: {exc}") from exc

        if not isinstance(data, list):
            raise CommandError("Manifest must be a JSON array of objects.")

        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise CommandError(f"Manifest item {index} is not an object.")

        return data

    def _ensure_impact_category(self, dry_run=False):
        impact_category = Category.objects.filter(title__icontains="impact").first()
        if impact_category:
            changed = False
            if not impact_category.active:
                impact_category.active = True
                changed = True
            if not impact_category.public:
                impact_category.public = True
                changed = True

            if changed:
                if dry_run:
                    self.stdout.write(f"Would update category '{impact_category.title}' to active/public.")
                else:
                    impact_category.save(update_fields=["active", "public", "modified"])
            return impact_category

        if dry_run:
            self.stdout.write("Would create Impact category.")
            return Category(title="Impact", icon="", active=True, public=True)

        impact_category = Category.objects.create(title="Impact", icon="", active=True, public=True)
        self.stdout.write(self.style.SUCCESS("Created Impact category."))
        return impact_category

    def _ensure_required_subcategories(self, impact_category, dry_run=False):
        subcategories = {}

        if dry_run and not getattr(impact_category, "pk", None):
            for title in REQUIRED_IMPACT_SUBCATEGORIES:
                self.stdout.write(f"Would create Impact subcategory '{title}'.")
                subcategories[title.lower()] = SubCategory(
                    category=impact_category,
                    title=title,
                    active=True,
                    public=True,
                )
            return subcategories

        for title in REQUIRED_IMPACT_SUBCATEGORIES:
            subcat = SubCategory.objects.filter(category=impact_category, title__iexact=title).first()

            if not subcat:
                if dry_run:
                    self.stdout.write(f"Would create Impact subcategory '{title}'.")
                    subcategories[title.lower()] = SubCategory(category=impact_category, title=title, active=True, public=True)
                    continue

                subcat = SubCategory.objects.create(category=impact_category, title=title, active=True, public=True)
                self.stdout.write(self.style.SUCCESS(f"Created Impact subcategory '{title}'."))
            else:
                changed = False
                if not subcat.active:
                    subcat.active = True
                    changed = True
                if not subcat.public:
                    subcat.public = True
                    changed = True

                if changed:
                    if dry_run:
                        self.stdout.write(f"Would update subcategory '{title}' to active/public.")
                    else:
                        subcat.save(update_fields=["active", "public"])

            subcategories[title.lower()] = subcat

        return subcategories

    def _normalize_subcategory_name(self, value):
        return str(value).strip().lower()

    def _upsert_dataset(
        self,
        *,
        impact_category,
        subcategory,
        title,
        slug,
        summary,
        published,
        public,
        can_clip,
        multi_temporal,
        initial_visible,
        time_parameter,
        time_prefix,
        current_time_method,
        dry_run=False,
    ):
        dataset = Dataset.objects.filter(dataset_slug=slug).first()
        action = "update" if dataset else "create"

        if not dataset:
            dataset = Dataset.objects.filter(title__iexact=title, layer_type="raster_file").first()
            if dataset:
                action = "update"

        if dry_run:
            self.stdout.write(f"Would {action} dataset '{title}' ({slug}).")
            if not dataset:
                dataset = Dataset(
                    title=title,
                    dataset_slug=slug,
                    layer_type="raster_file",
                    category=impact_category,
                    sub_category=subcategory,
                )
            return dataset

        if not dataset:
            dataset = Dataset.objects.create(
                title=title,
                category=impact_category,
                sub_category=subcategory,
                summary=summary,
                layer_type="raster_file",
                dataset_slug=slug,
                time_parameter=time_parameter,
                time_prefix=time_prefix,
                published=published,
                public=public,
                initial_visible=initial_visible,
                multi_temporal=multi_temporal,
                multi_layer=False,
                near_realtime=False,
                current_time_method=current_time_method,
                can_clip=can_clip,
            )
            self.stdout.write(self.style.SUCCESS(f"Created dataset '{title}' ({slug})."))
            return dataset

        dataset.title = title
        dataset.category = impact_category
        dataset.sub_category = subcategory
        dataset.summary = summary
        dataset.layer_type = "raster_file"
        dataset.dataset_slug = slug
        dataset.time_parameter = time_parameter
        dataset.time_prefix = time_prefix
        dataset.published = published
        dataset.public = public
        dataset.initial_visible = initial_visible
        dataset.multi_temporal = multi_temporal
        dataset.current_time_method = current_time_method
        dataset.can_clip = can_clip
        dataset.save()
        self.stdout.write(self.style.SUCCESS(f"Updated dataset '{title}' ({slug})."))
        return dataset

    def _upsert_layer(self, *, dataset, title, date_format, directory_name, dry_run=False):
        layer = None
        action = "create"

        if getattr(dataset, "pk", None):
            layer = dataset.raster_file_layers.filter(title__iexact=title).first()
            action = "update" if layer else "create"

            if not layer:
                layer = dataset.raster_file_layers.first()
                if layer:
                    action = "update"

        conflict_qs = RasterFileLayer.objects.filter(auto_ingest_custom_directory_name=directory_name)
        if layer:
            conflict_qs = conflict_qs.exclude(pk=layer.pk)

        conflict = conflict_qs.first()
        if conflict:
            raise CommandError(
                "Directory name conflict: "
                f"'{directory_name}' is already used by layer '{conflict.title}' ({conflict.pk})."
            )

        if dry_run:
            self.stdout.write(
                f"Would {action} raster layer '{title}' for dataset '{dataset.dataset_slug}' with directory '{directory_name}'."
            )
            if not layer:
                layer = RasterFileLayer(
                    dataset=dataset,
                    title=title,
                    default=True,
                    date_format=date_format,
                    auto_ingest_from_directory=True,
                    auto_ingest_use_custom_directory_name=True,
                    auto_ingest_custom_directory_name=directory_name,
                )
            return layer

        if not layer:
            layer = RasterFileLayer.objects.create(
                dataset=dataset,
                title=title,
                default=True,
                date_format=date_format,
                auto_ingest_from_directory=True,
                auto_ingest_use_custom_directory_name=True,
                auto_ingest_custom_directory_name=directory_name,
            )
            self.stdout.write(self.style.SUCCESS(f"Created raster layer '{title}' for '{dataset.dataset_slug}'."))
            return layer

        layer.title = title
        layer.date_format = date_format
        layer.default = True
        layer.auto_ingest_from_directory = True
        layer.auto_ingest_use_custom_directory_name = True
        layer.auto_ingest_custom_directory_name = directory_name
        layer.save()
        self.stdout.write(self.style.SUCCESS(f"Updated raster layer '{title}' for '{dataset.dataset_slug}'."))
        return layer

    def _run_ingest(self, ingest_targets, *, overwrite=False, clip=False, dry_run=False):
        auto_ingest_root = geomanager_settings.get("auto_ingest_raster_data_dir")
        if not auto_ingest_root:
            raise CommandError("GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR is not configured.")

        root_path = Path(auto_ingest_root)
        if not root_path.is_absolute():
            raise CommandError("GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR must be an absolute path.")

        for dataset_slug, directory_name, _layer_id in ingest_targets:
            directory_path = root_path / directory_name

            if not directory_path.exists():
                logger.warning(
                    "Skipping ingest for %s: directory does not exist: %s",
                    dataset_slug,
                    directory_path,
                )
                self.stdout.write(self.style.WARNING(f"Skip {dataset_slug}: missing directory {directory_path}"))
                continue

            files = sorted(
                [
                    p
                    for p in directory_path.iterdir()
                    if p.is_file() and p.suffix.lower() in SUPPORTED_RASTER_EXTENSIONS
                ]
            )

            if not files:
                self.stdout.write(self.style.WARNING(f"Skip {dataset_slug}: no .tif/.nc files in {directory_path}"))
                continue

            self.stdout.write(
                f"Ingesting {len(files)} files for {dataset_slug} from {directory_path} "
                f"(overwrite={overwrite}, clip={clip})"
            )

            for file_path in files:
                if dry_run:
                    self.stdout.write(f"Would ingest {file_path}")
                    continue

                ingest_raster_file(str(file_path), overwrite=overwrite, clip_to_boundary=clip)

            self.stdout.write(self.style.SUCCESS(f"Ingest complete for {dataset_slug}."))
