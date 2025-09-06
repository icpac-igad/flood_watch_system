from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from Impact.models import Admin1  # Replace with your actual app name
import os
from django.conf import settings

# Define the shapefile path using a more robust approach
BASE_DIR = settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
shapefile_path = os.path.join(BASE_DIR, "Impact", "static_data", "GHA_Admin0.shp")

# Define Layer Mapping
admin1_mapping = {
    'objectid': 'OBJECTID',
    'country': 'COUNTRY',
    'area': 'area',
    'shape_leng': 'Shape_Leng',
    'shape_area': 'Shape_Area',
    'land_under': 'land_under',
    'geom': 'MULTIPOLYGON',  # Corrected field name
}

class Command(BaseCommand):
    help = "Import shapefile data into the Admin1 model"
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting shapefile import..."))
        
        # Print the path we're using for debugging
        self.stdout.write(f"Looking for shapefile at: {shapefile_path}")
        
        if not os.path.exists(shapefile_path):
            self.stderr.write(self.style.ERROR(f"Shapefile not found at {shapefile_path}"))
            return
        
        try:
            lm = LayerMapping(Admin1, shapefile_path, admin1_mapping, transform=False, encoding='utf-8')
            lm.save(strict=True, verbose=True)
            self.stdout.write(self.style.SUCCESS("Data import completed successfully!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error importing data: {e}"))