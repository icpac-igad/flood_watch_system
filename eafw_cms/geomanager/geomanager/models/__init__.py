import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from wagtailcache.cache import clear_cache

from .aoi import *
from .boundary import *
from .core import *
from .dataset_sync import *
from .geomanager_settings import *
from .geostore import *
from .profile import *
from .raster_file import *
from .raster_tile import *
from .tile_gl import *
from .vector_file import *
from .vector_tile import *
from .watcher import *
from .wms import *
from .raster_style import *

logger = logging.getLogger(__name__)


# clear wagtail cache on saving the following models
@receiver(post_save, sender=Category)
@receiver(post_save, sender=SubCategory)
@receiver(post_save, sender=Dataset)
@receiver(post_save, sender=Metadata)
@receiver(post_save, sender=WmsRasterDatasetSync)
@receiver(post_save, sender=WatcherConfig)
@receiver(post_save, sender=GeomanagerSettings)
@receiver(post_save, sender=RasterFileLayer)
@receiver(post_save, sender=LayerRasterFile)
@receiver(post_save, sender=RasterStyle)
@receiver(post_save, sender=RasterTileLayer)
@receiver(post_save, sender=WmsLayer)
@receiver(post_save, sender=MBTSource)
@receiver(post_save, sender=VectorFileLayer)
@receiver(post_save, sender=VectorTileLayer)
@receiver(post_save, sender=PgVectorTable)
@receiver(post_save, sender=AdditionalMapBoundaryData)
@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=SubCategory)
@receiver(post_delete, sender=Dataset)
@receiver(post_delete, sender=Metadata)
@receiver(post_delete, sender=WmsRasterDatasetSync)
@receiver(post_delete, sender=WatcherConfig)
@receiver(post_delete, sender=GeomanagerSettings)
@receiver(post_delete, sender=RasterFileLayer)
@receiver(post_delete, sender=LayerRasterFile)
@receiver(post_delete, sender=RasterStyle)
@receiver(post_delete, sender=RasterTileLayer)
@receiver(post_delete, sender=WmsLayer)
@receiver(post_delete, sender=MBTSource)
@receiver(post_delete, sender=VectorFileLayer)
@receiver(post_delete, sender=VectorTileLayer)
@receiver(post_delete, sender=PgVectorTable)
@receiver(post_delete, sender=AdditionalMapBoundaryData)
def handle_clear_wagtail_cache(sender, **kwargs):
    logger.info("[WAGTAIL_CACHE]: Clearing cache")
    clear_cache()
