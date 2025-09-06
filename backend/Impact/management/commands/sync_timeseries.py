from django.core.management.base import BaseCommand
import geopandas as gpd
from Impact.models import SectorForecast, SectorData
from datetime import datetime
from django.utils import timezone
from django.db import transaction
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync sector time series data from GeoJSON and upload to database'

    GEOJSON_FILENAME = './temp_data/merged_data.geojson'
    BATCH_SIZE = 1000  # Number of records to process in each batch

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-existing',
            action='store_true',
            help='Keep existing forecast data instead of clearing it',
        )

    def handle(self, *args, **kwargs):
        try:
            self.process_time_series(self.GEOJSON_FILENAME, kwargs.get('keep_existing', False))
        except Exception as e:
            logger.error(f'Error processing time series: {str(e)}')
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))

    def validate_forecast_value(self, value):
        try:
            if value:
                return float(value)
            return None
        except ValueError:
            return None

    @transaction.atomic
    def process_time_series(self, geojson_path, keep_existing=False):
        logger.info(f"Loading sector data from {geojson_path}...")
        
        try:
            gdf = gpd.read_file(geojson_path)
            
            if not keep_existing:
                logger.info("Clearing existing forecast data...")
                SectorForecast.objects.all().delete()

            forecasts_to_create = []
            
            for _, row in gdf.iterrows():
                section_code = row['SEC_CODE']
                
                try:
                    sector = SectorData.objects.get(sec_code=section_code)
                except SectorData.DoesNotExist:
                    logger.warning(f"Sector with code {section_code} not found.")
                    continue

                # Extract and validate time series data
                try:
                    gfs_data = row['time_series_discharge_simulated-gfs'].split(',')
                    icon_data = row['time_series_discharge_simulated-icon'].split(',')
                    
                    if isinstance(row['time_period'], str):
                        time_periods = row['time_period'].split(',')
                        date_parser = lambda x: self.make_aware(datetime.strptime(x.strip(), '%Y-%m-%d %H:%M'))
                    elif hasattr(row['time_period'], '__iter__'):
                        time_periods = row['time_period']
                        date_parser = lambda x: self.make_aware(x)
                    else:
                        time_periods = [row['time_period']] * len(gfs_data)
                        date_parser = lambda x: self.make_aware(x)

                    for gfs_value, icon_value, time_period in zip(gfs_data, icon_data, time_periods):
                        date = date_parser(time_period)
                        
                        # Validate and create GFS forecast
                        gfs_val = self.validate_forecast_value(gfs_value)
                        if gfs_val is not None:
                            forecasts_to_create.append(
                                SectorForecast(
                                    sector=sector,
                                    model_type='GFS',
                                    time_point=date,
                                    forecast_value=gfs_val
                                )
                            )

                        # Validate and create ICON forecast
                        icon_val = self.validate_forecast_value(icon_value)
                        if icon_val is not None:
                            forecasts_to_create.append(
                                SectorForecast(
                                    sector=sector,
                                    model_type='ICON',
                                    time_point=date,
                                    forecast_value=icon_val
                                )
                            )

                        # Bulk create when batch size is reached
                        if len(forecasts_to_create) >= self.BATCH_SIZE:
                            SectorForecast.objects.bulk_create(
                                forecasts_to_create,
                                ignore_conflicts=True
                            )
                            forecasts_to_create = []

                except (KeyError, ValueError) as e:
                    logger.error(f"Error processing row with section_code {section_code}: {str(e)}")
                    continue

            # Create any remaining forecasts
            if forecasts_to_create:
                SectorForecast.objects.bulk_create(
                    forecasts_to_create,
                    ignore_conflicts=True
                )

            logger.info("Time series data successfully pushed to SectorForecast model.")
            self.stdout.write(self.style.SUCCESS("Time series data pushed to SectorForecast model."))
            
        except Exception as e:
            logger.error(f"Error processing time series data: {str(e)}")
            raise

    def make_aware(self, naive_datetime):
        """Make a naive datetime object timezone-aware."""
        if timezone.is_naive(naive_datetime):
            return timezone.make_aware(naive_datetime, timezone.get_default_timezone())
        return naive_datetime