"""
Runtime patches for upstream geomanager package.

These fix bugs in the installed geomanager that haven't been merged upstream yet.
Each patch is idempotent and logs what it does so issues are easy to trace.
Remove individual patches as upstream fixes land.
"""
import logging

logger = logging.getLogger(__name__)


def patch_tile_url_query_separator():
    """Fix tile_base.py: use & instead of ? when base_url already has a query string.

    Without this, WMS URLs like /mapserver/?SERVICE=WMS&...&BBOX={bbox}
    get ?time={{time}} appended (double ?) instead of &time={{time}}.
    """
    from geomanager.models.tile_base import TileLayerAbstract

    original_tile_url = TileLayerAbstract.tile_url.fget

    @property
    def patched_tile_url(self):
        tile_url = self.base_url
        query_params = {}

        if self.has_time:
            time_param_name = self.time_parameter_name or "time"
            query_params.update({time_param_name: "{{time}}"})

        static_params = self.get_static_params()
        if static_params:
            query_params.update(static_params)

        query_str = "&".join([f"{key}={value}" for key, value in query_params.items()])

        if query_str:
            sep = "&" if "?" in tile_url else "?"
            tile_url = f"{tile_url}{sep}{query_str}"

        return tile_url

    TileLayerAbstract.tile_url = patched_tile_url
    logger.info("patch: tile_base.py query separator fix applied")


def patch_dataset_viewset_flatten():
    """Fix DatasetViewSet.list: flatten nested lists from hooks.

    The register_geomanager_datasets hook returns boundary datasets as a
    nested list [[ds1, ds2, ds3]], which breaks the mapviewer's dataset
    indexing. This patch flattens any nested lists in the hook results.
    """
    from geomanager.viewsets.core import DatasetViewSet
    from rest_framework.response import Response
    from wagtail import hooks

    geomanager_register_datasets_hook_name = "register_geomanager_datasets"

    original_list = DatasetViewSet.list

    def patched_list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        dataset_with_layers = []
        datasets = []

        for fn in hooks.get_hooks(geomanager_register_datasets_hook_name):
            hook_datasets = fn(request)
            if isinstance(hook_datasets, list):
                for dataset in hook_datasets:
                    if isinstance(dataset, list):
                        datasets.extend(dataset)
                    else:
                        datasets.append(dataset)

        for dataset in queryset:
            if dataset.has_layers():
                if dataset.requires_file_upload and not dataset.has_files:
                    continue
                dataset_with_layers.append(dataset)

        serializer = self.get_serializer(dataset_with_layers, many=True)
        geomanager_datasets = serializer.data

        if geomanager_datasets:
            datasets.extend(geomanager_datasets)

        return Response(datasets)

    DatasetViewSet.list = patched_list
    logger.info("patch: DatasetViewSet nested list flatten fix applied")


def apply_all():
    """Apply all patches. Called from HomeConfig.ready()."""
    patch_tile_url_query_separator()
    patch_dataset_viewset_flatten()
    logger.info("All geomanager patches applied")
