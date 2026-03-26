import datetime
import pytz
from pathlib import Path
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import filesizeformat
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from wagtail.admin.auth import (
    user_passes_test,
    user_has_any_page_permission,
    permission_denied,
)
from wagtail.models import Site
from wagtail.snippets.permissions import get_permission_name
from wagtail_modeladmin.helpers import AdminURLHelper

from geomanager.forms import LayerRasterFileForm
from geomanager.models import Category, Dataset, WmsLayer, GeomanagerSettings, WmsRasterUpload
from geomanager.utils.raster_utils import (
    read_raster_info,
)

ALLOWED_RASTER_EXTENSIONS = ["tif", "tiff", "geotiff", "nc"]


@user_passes_test(user_has_any_page_permission)
def upload_wms_raster_file(request, dataset_id=None, layer_id=None):
    permission = get_permission_name("change", Dataset)
    if not request.user.has_perm(permission):
        return permission_denied(request)

    edit_form_template = "geomanager/raster_file/raster_file_edit_form.html"

    site = Site.objects.get(is_default_site=True)
    layer_manager_settings = GeomanagerSettings.for_site(site)

    file_error_messages = {
        "invalid_file_extension": _("Not a supported raster format. Supported formats: %(supported_formats)s.")
        % {"supported_formats": ALLOWED_RASTER_EXTENSIONS},
        "file_too_large": _(
            "This file is too big (%(file_size)s). Maximum filesize %(max_filesize)s. "
            "You can adjust the Maximum upload file size under Geomanager settings"
        ),
        "file_too_large_unknown_size": _(
            "This file is too big. Maximum filesize %(max_filesize)s. "
            "You can adjust the Maximum upload file size under Geomanager settings."
        )
        % {"max_filesize": filesizeformat(layer_manager_settings.max_upload_size_bytes)},
    }

    layer = None
    context = {}
    context.update(
        {
            "max_filesize": layer_manager_settings.max_upload_size_bytes,
            "allowed_extensions": ALLOWED_RASTER_EXTENSIONS,
            "error_max_file_size": file_error_messages["file_too_large_unknown_size"],
            "error_accepted_file_types": file_error_messages["invalid_file_extension"],
        }
    )

    dataset = get_object_or_404(Dataset, pk=dataset_id)

    category_admin_helper = AdminURLHelper(Category)
    categories_url = category_admin_helper.get_action_url("index")

    admin_url_helper = AdminURLHelper(Dataset)
    dataset_list_url = admin_url_helper.get_action_url("index")
    layer_upload_url = reverse("geomanager_dataset_upload_wms_raster", args=[dataset.pk])
    layer_list_url = None
    layer_preview_url = None

    if layer_id:
        layer = get_object_or_404(WmsLayer, pk=layer_id)
        layer_admin_url_helper = AdminURLHelper(layer)
        layer_list_url = layer_admin_url_helper.get_action_url("index") + f"?dataset__id__exact={str(dataset.pk)}"
        layer_preview_url = layer.preview_url
        layer_upload_url = reverse("geomanager_dataset_layer_upload_wms_raster", args=[dataset.pk, layer.pk])

    navigation_items = [
        {"url": categories_url, "label": Category._meta.verbose_name_plural},
        {"url": dataset_list_url, "label": Dataset._meta.verbose_name_plural},
        {"url": layer_list_url, "label": WmsLayer._meta.verbose_name_plural},
        {"url": "#", "label": _("Upload Raster Files")},
    ]

    context.update(
        {
            "dataset": dataset,
            "layer": layer,
            "datasets_index_url": dataset_list_url,
            "layers_index_url": layer_list_url,
            "dataset_preview_url": dataset.preview_url,
            "layer_upload_url": layer_upload_url,
            "simple_upload_url": reverse("geomanager_dataset_upload_wms_raster", args=[dataset.pk]),
            "layer_preview_url": layer_preview_url,
            "navigation_items": navigation_items,
        }
    )

    # Check if user is submitting
    if request.method == "POST":
        files = request.FILES.getlist("files[]", None)
        file_path = Path(f"/tmp/{files[0].name}")
        # delete existing file to prevent automatic renaming of the file
        if file_path.exists():
            file_path.unlink(missing_ok=True)

        FileSystemStorage(location="/tmp").save(files[0].name, files[0])
        raster_metadata = read_raster_info(file_path)

        print("uploaded raster metadata", raster_metadata)

        query_set = WmsLayer.objects.filter(dataset=dataset)

        print("WMS Layer Qset", query_set)

        initial_data = {"layer": layer_id if layer_id else query_set.first()}

        form_kwargs = {}

        timestamps = raster_metadata.get("timestamps", None)

        if timestamps:
            form_kwargs.update({"nc_dates_choices": timestamps})
            initial_data.update({"nc_dates": timestamps})

        print("initial form data", initial_data)

        data_variables = raster_metadata.get("data_variables", None)

        print("nc data variables", data_variables)

        layer_form = LayerRasterFileForm(queryset=query_set, initial=initial_data, **form_kwargs)
        layer_forms = []

        if data_variables and len(data_variables) > 0:
            for variable in data_variables:
                form_init_data = {**initial_data, "nc_data_variable": variable}
                l_form = LayerRasterFileForm(queryset=query_set, initial=form_init_data, **form_kwargs)
                layer_forms.append({"data_variable": variable, "form": l_form})

        ctx = {
            "dataset": dataset,
            "publish_action": reverse("geomanager_publish_wms_raster"),
            "delete_action": reverse("geomanager_delete_wms_raster_upload"),
            "multiple_vars": True if len(data_variables) > 1 else False,
        }

        response = {
            "success": True,
        }
        print("layer_forms", layer_forms)
        print("context", ctx)
        # we have more than one layer, render multiple forms
        if layer_forms:
            forms = []
            for form in layer_forms:
                ctx.update({**form})
                forms.append(
                    render_to_string(
                        edit_form_template,
                        ctx,
                        request=request,
                    )
                )
            response.update({"forms": forms})
        else:
            ctx.update({"form": layer_form})
            form = render_to_string(edit_form_template, ctx, request=request)
            response.update({"form": form})

        return JsonResponse(response)

    return render(request, "geomanager/raster_file/raster_file_upload.html", context)


@user_passes_test(user_has_any_page_permission)
def publish_wms_raster(request):
    if request.method != "POST":
        return JsonResponse({"message": _("Only POST allowed")})

    print("layer", request.POST.get("layer"))

    db_layer = get_object_or_404(WmsLayer, pk=request.POST.get("layer"))

    data = {
        "layer": db_layer,
        "time": request.POST.get("time"),
        "nc_data_variable": request.POST.get("nc_data_variable"),
    }

    if request.POST.get("nc_dates"):
        data.update({"nc_dates": request.POST.getlist("nc_dates")})

    print("dataset publish data", data)
    print(db_layer.dataset)

    layer_form = LayerRasterFileForm(data=data)

    ctx = {
        "dataset": db_layer.dataset,
        "publish_action": reverse("geomanager_publish_wms_raster"),
        "delete_action": reverse("geomanager_delete_wms_raster_upload"),
        "form": layer_form,
    }

    def get_response():
        return {
            "success": False,
            "form": render_to_string(
                "geomanager/raster_file/raster_file_edit_form.html",
                ctx,
                request=request,
            ),
        }

    if layer_form.is_valid():
        # layer = layer_form.cleaned_data["layer"]
        time = layer_form.cleaned_data["time"]
        nc_dates = layer_form.cleaned_data["nc_dates"]
        nc_data_variable = layer_form.cleaned_data["nc_data_variable"]

        if nc_dates:
            # data_timestamps = raster_metadata.get("timestamps")

            for time_str in nc_dates:
                try:
                    # index = data_timestamps.index(time_str)

                    d_time = datetime.datetime.fromisoformat(time_str)

                    # Make the datetime object timezone aware. We assume the time is in standard UTC
                    d_time = d_time.replace(tzinfo=pytz.UTC)

                    exists = WmsRasterUpload.objects.filter(layer=db_layer, time=d_time).exists()

                    if exists:
                        error_message = _("File with date %(time_str)s already exists for layer %(db_layer)s") % {
                            "time_str": time_str,
                            "db_layer": db_layer,
                        }
                        layer_form.add_error("nc_dates", error_message)
                        return JsonResponse(get_response())

                    # create_layer_raster_file(
                    #     layer, upload, time=d_time, band_index=str(index), data_variable=nc_data_variable
                    # )
                except Exception:
                    layer_form.add_error(None, _("Error occurred. Try again"))
                    return JsonResponse(get_response())
            return JsonResponse(
                {
                    "success": True,
                }
            )
        elif nc_data_variable:
            exists = WmsRasterUpload.objects.filter(layer=db_layer, time=time).exists()

            if exists:
                error_message = _("File with date %(time)s already exists for layer %(db_layer)s") % {
                    "time": time.isoformat(),
                    "db_layer": db_layer,
                }
                layer_form.add_error("time", error_message)
                return JsonResponse(get_response())

            # create_layer_raster_file(layer, upload, time, data_variable=nc_data_variable)
            # cleanup upload
            return JsonResponse(
                {
                    "success": True,
                }
            )
        else:
            exists = WmsLayer.objects.filter(layer=db_layer, time=time).exists()

            if exists:
                error_message = _("File with date %(time)s already exists for selected layer") % {
                    "time": time.isoformat()
                }
                layer_form.add_error("time", error_message)
                return JsonResponse(get_response())

            # create_layer_raster_file(layer, upload, time)
        # cleanup upload
        return JsonResponse(
            {
                "success": True,
            }
        )
    else:
        return JsonResponse(get_response())


@user_passes_test(user_has_any_page_permission)
def delete_wms_raster_upload(request):
    if request.method != "POST":
        return JsonResponse({"message": _("Only POST allowed")})
    return JsonResponse({"success": True})
