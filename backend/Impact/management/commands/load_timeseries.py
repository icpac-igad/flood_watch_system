import os
import json
import geopandas as gpd
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from Impact.models import RiverSection

class Command(BaseCommand):
    help = 'Sync river sections timeseries data from GeoJSON'

    def handle(self, *args, **kwargs):
        # Absolute path to the GeoJSON file
        geojson_path = './temp_data/merged_data.geojson'
        
        # Validate file path
        if not os.path.exists(geojson_path):
            self.stderr.write(self.style.ERROR(f'File not found: {geojson_path}'))
            return
        
        try:
            gdf = gpd.read_file(geojson_path)
            
            imported_count = 0
            for _, row in gdf.iterrows():
                props = row.to_dict()
                
                # Find or create RiverSection
                river_section, created = RiverSection.objects.get_or_create(
                    name=props.get('section_name', 'Unnamed Section'),
                    defaults={
                        'latitude': row.geometry.y,
                        'longitude': row.geometry.x,
                        'geom': Point(row.geometry.x, row.geometry.y, srid=4326)
                    }
                )
                
                # Handle time periods and discharge values
                time_periods = props.get('time_period', '')
                gfs_discharge = props.get('time_series_discharge_simulated-gfs', '')
                icon_discharge = props.get('time_series_discharge_simulated-icon', '')
                
                # Convert Timestamps to strings if needed
                if hasattr(time_periods, 'dt'):
                    time_periods = time_periods.dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
                elif isinstance(time_periods, str):
                    time_periods = time_periods.split(',')
                
                # Convert discharge values to list of floats
                if hasattr(gfs_discharge, 'tolist'):
                    gfs_discharge = gfs_discharge.tolist()
                elif isinstance(gfs_discharge, str):
                    gfs_discharge = [float(x) for x in gfs_discharge.split(',') if x.strip()]
                
                if hasattr(icon_discharge, 'tolist'):
                    icon_discharge = icon_discharge.tolist()
                elif isinstance(icon_discharge, str):
                    icon_discharge = [float(x) for x in icon_discharge.split(',') if x.strip()]
                
                # Update timeseries data
                river_section.models_data = {
                    'GFS': {
                        'time_periods': time_periods,
                        'discharge_values': gfs_discharge
                    },
                    'ICON': {
                        'time_periods': time_periods,
                        'discharge_values': icon_discharge
                    }
                }
                river_section.save()
                imported_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully synced {imported_count} river sections timeseries'))
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error syncing data: {str(e)}'))
            import traceback
            traceback.print_exc()