import pytz
from datetime import datetime
from django.conf.global_settings import TIME_ZONE
from rest_framework import mixins, viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.exceptions import NotAcceptable
from wagtail import hooks
from django.shortcuts import get_object_or_404
from geomanager import serializers
from geomanager.models import Dataset, WmsDatasetIndex, Metadata
from geomanager.utils.forecast_datasets import patch_forecast_datasets

geomanager_register_datasets_hook_name = "register_geomanager_datasets"


class DatasetViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Dataset.objects.filter(published=True)
    serializer_class = serializers.DatasetSerializer

    renderer_classes = [JSONRenderer]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        dataset_with_layers = []

        datasets = []

        # get datasets from registered hooks
        for fn in hooks.get_hooks(geomanager_register_datasets_hook_name):
            hook_datasets = fn(request)
            if isinstance(hook_datasets, list):
                for dataset in hook_datasets:
                    datasets.append(dataset)

        # get only datasets with layers defined
        for dataset in queryset:
            if dataset.has_layers():
                # if dataset requires file upload, but has no files, skip
                if dataset.requires_file_upload and not dataset.has_files:
                    continue
                dataset_with_layers.append(dataset)

        serializer = self.get_serializer(dataset_with_layers, many=True)
        geomanager_datasets = serializer.data

        if geomanager_datasets:
            datasets.extend(geomanager_datasets)

        patch_forecast_datasets(request, datasets)
        return Response(datasets)


class DatasetSlugViewSet(mixins.UpdateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Dataset.objects.exclude(dataset_slug=None)
    serializer_class = serializers.DatasetDetailSerializer
    lookup_field = "dataset_slug"
    renderer_classes = [JSONRenderer]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def update(self, request, *args, **kwargs):
        # update dataset latest date if in API payload
        api_date_format = "%Y-%m-%d" if "date_format" not in request.data.keys() else request.data["date_format"]
        if "latest_date" in request.data.keys():
            dataset = get_object_or_404(Dataset, dataset_slug=kwargs["dataset_slug"])
            local_tz = pytz.timezone(TIME_ZONE)
            api_date = local_tz.localize(datetime.strptime(request.data["latest_date"], api_date_format))
            if dataset.latest_date is None or dataset.latest_date < api_date:
                dataset.latest_date = api_date
            if "summary" in request.data.keys():
                dataset.summary = request.data["summary"]
            dataset.save()
            # add api date into dataset dates index
            if not len(dataset.wms_datasets.filter(datetime=api_date)):
                dataset_index = WmsDatasetIndex.objects.create(datetime=api_date, dataset=dataset)
                dataset_index.save()
            # return request payload
            return Response(request.data)
        else:
            raise NotAcceptable(detail="route implemented for uopdating dataset date only!")


class MetadataViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Metadata.objects.all()
    serializer_class = serializers.MetadataSerialiazer
