#!/usr/bin/env python3
"""
MapServer Configuration Updater
Dynamically updates MapServer map files with latest raster file paths from database
"""

import os
import re
from datetime import datetime
from django.db import connection
from django.conf import settings


class MapServerUpdater:
    """Updates MapServer configuration with latest data file paths."""
    
    def __init__(self, map_template_path, output_map_path):
        """Initialize with template and output paths."""
        self.map_template_path = map_template_path
        self.output_map_path = output_map_path
        
    def get_latest_raster_paths(self):
        """Get latest raster file paths from database."""
        paths = {}
        
        with connection.cursor() as cursor:
            # Get latest alert level rasters for each group
            cursor.execute("""
                SELECT DISTINCT ON (alert_group)
                    alert_group, file_path, data_date, time_run
                FROM Impact_alertlevelraster
                WHERE file_path IS NOT NULL
                ORDER BY alert_group, data_date DESC, time_run DESC
            """)
            
            for row in cursor.fetchall():
                alert_group, file_path, data_date, time_run = row
                paths[f'alert_{alert_group}_latest'] = file_path
                
            # Get latest flood hazard map
            cursor.execute("""
                SELECT file_path, data_date, time_run
                FROM Impact_floodhazardmapraster
                WHERE file_path IS NOT NULL
                ORDER BY data_date DESC, time_run DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                file_path, data_date, time_run = result
                paths['flood_hazard_latest'] = file_path
                
        return paths
    
    def update_map_file(self, dynamic_paths=None):
        """Update MapServer map file with latest paths."""
        if dynamic_paths is None:
            dynamic_paths = self.get_latest_raster_paths()
            
        # Read template
        with open(self.map_template_path, 'r') as f:
            map_content = f.read()
            
        # Replace placeholders with actual paths
        base_prefix = str(settings.BASE_DIR) + os.sep

        for key, path in dynamic_paths.items():
            placeholder = f"{{{{ {key.upper()}_PATH }}}}"
            if placeholder in map_content:
                # Make path relative if needed
                if path.startswith(base_prefix):
                    relative_path = path.replace(base_prefix, '')
                    map_content = map_content.replace(placeholder, relative_path)
                else:
                    map_content = map_content.replace(placeholder, path)
                    
        # Add timestamp comment
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        map_content = f"# Auto-generated: {timestamp}\n" + map_content
        
        # Write updated map file
        with open(self.output_map_path, 'w') as f:
            f.write(map_content)
            
        return dynamic_paths
    
    def create_symlinks(self, symlink_dir='/tmp/mapserver_latest'):
        """Create symlinks to latest files for stable MapServer paths."""
        paths = self.get_latest_raster_paths()
        
        # Create symlink directory if it doesn't exist
        os.makedirs(symlink_dir, exist_ok=True)
        
        symlinks = {}
        for key, source_path in paths.items():
            if os.path.exists(source_path):
                # Create stable symlink name
                ext = os.path.splitext(source_path)[1]
                symlink_path = os.path.join(symlink_dir, f'{key}{ext}')
                
                # Remove old symlink if exists
                if os.path.islink(symlink_path):
                    os.unlink(symlink_path)
                    
                # Create new symlink
                os.symlink(source_path, symlink_path)
                symlinks[key] = symlink_path
                print(f"Created symlink: {symlink_path} -> {source_path}")
                
        return symlinks
    
    def generate_time_based_layers(self, start_date=None, end_date=None):
        """Generate MapServer layers for specific time range."""
        layers = []
        
        with connection.cursor() as cursor:
            query = """
                SELECT alert_group, file_path, data_date, time_run
                FROM Impact_alertlevelraster
                WHERE file_path IS NOT NULL
            """
            
            params = []
            if start_date:
                query += " AND data_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND data_date <= %s"
                params.append(end_date)
                
            query += " ORDER BY data_date, time_run, alert_group"
            
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                alert_group, file_path, data_date, time_run = row
                
                # Generate layer configuration
                layer_name = f"alert_{alert_group}_{data_date.strftime('%Y%m%d')}_{time_run}"
                layer_config = self._generate_raster_layer(
                    name=layer_name,
                    title=f"Alert {alert_group} - {data_date} {time_run}",
                    data_path=file_path,
                    layer_type='alert'
                )
                layers.append(layer_config)
                
        return layers
    
    def _generate_raster_layer(self, name, title, data_path, layer_type='alert'):
        """Generate MapServer LAYER configuration for a raster."""
        if layer_type == 'alert':
            classes = """
    CLASSITEM "[pixel]"
    CLASS
      NAME "No Alert"
      EXPRESSION ([pixel] = 0)
      STYLE
        COLOR 255 255 255
        OPACITY 0
      END
    END
    
    CLASS
      NAME "Alert Level 1"
      EXPRESSION ([pixel] = 1)
      STYLE
        COLOR 45 210 247
        OPACITY 70
      END
    END
    
    CLASS
      NAME "Alert Level 2"
      EXPRESSION ([pixel] = 2)
      STYLE
        COLOR 255 255 0
        OPACITY 80
      END
    END
    
    CLASS
      NAME "Alert Level 3"
      EXPRESSION ([pixel] = 3)
      STYLE
        COLOR 255 128 0
        OPACITY 90
      END
    END
    
    CLASS
      NAME "Alert Level 4"
      EXPRESSION ([pixel] = 4)
      STYLE
        COLOR 255 0 0
        OPACITY 100
      END
    END"""
        else:  # flood hazard
            classes = """
    CLASSITEM "[pixel]"
    CLASS
      NAME "No Flood"
      EXPRESSION ([pixel] = 0)
      STYLE
        COLOR 255 255 255
        OPACITY 0
      END
    END
    
    CLASS
      NAME "Flood Area"
      EXPRESSION ([pixel] = 1)
      STYLE
        COLOR 0 100 255
        OPACITY 60
      END
    END"""
        
        layer = f"""
  LAYER
    NAME "{name}"
    STATUS ON
    TYPE RASTER
    DATA "{data_path}"
    
    PROJECTION
      "init=epsg:4326"
    END
    
    METADATA
      "wms_title" "{title}"
      "wms_enable_request" "*"
      "wms_format" "image/png"
    END
    
{classes}
  END
"""
        return layer


# Django management command integration
def update_mapserver_config():
    """Update MapServer configuration with latest file paths."""
    base_dir = settings.BASE_DIR
    updater = MapServerUpdater(
        map_template_path=os.path.join(base_dir, 'mapserver/config_clean/master.map'),
        output_map_path=os.path.join(base_dir, 'mapserver/config_clean/dynamic_layers.map')
    )
    
    # Create symlinks for stable paths
    symlinks = updater.create_symlinks()
    
    # Update map file
    paths = updater.update_map_file()
    
    return {
        'paths': paths,
        'symlinks': symlinks
    }
