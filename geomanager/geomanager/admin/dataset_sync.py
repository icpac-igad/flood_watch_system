from django.utils.translation import gettext_lazy as _
from geomanager.admin.base import BaseModelAdmin, ModelAdminCanHide
from geomanager.models.dataset_sync import WmsRasterDatasetSync


class WmsRasterSyncAdmin(BaseModelAdmin, ModelAdminCanHide):
    model = WmsRasterDatasetSync
    exclude_from_explorer = True
    menu_icon = "rotate"
    menu_label = _("WMS Raster Sync")
