import os
import shutil
from io import BytesIO
import paramiko
from datetime import datetime, timedelta
import geopandas as gpd
import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from decouple import config
from Impact.models import (
    AffectedPopulation, ImpactedGDP, AffectedCrops,
    AffectedRoads, DisplacedPopulation, AffectedLivestock,
    AffectedGrazingLand
)

current_date = datetime.now().strftime('%Y%m%d')

class Command(BaseCommand):
    help = 'Sync remote impact layer shapefiles from SFTP and upload to database and MapServer'
    
    TEMP_DIR = './temp_shapefiles'
    # Updated MapServer directory to save to data/shapefiles/impact_shapefiles with date
    MAPSERVER_DIR = f'../data/shapefiles/impact_shapefiles/{current_date}'
    
    model_configurations = {
        AffectedPopulation: f'{current_date}0000_FPimpacts-Population.shp',
        ImpactedGDP: f'{current_date}0000_FPimpacts-GDP.shp',
        AffectedCrops: f'{current_date}0000_FPimpacts-Crops.shp',
        AffectedRoads: f'{current_date}0000_FPimpacts-KmRoads.shp',
        DisplacedPopulation: f'{current_date}0000_FPimpacts-Displaced.shp',
        AffectedLivestock: f'{current_date}0000_FPimpacts-Livestock.shp',
        AffectedGrazingLand: f'{current_date}0000_FPimpacts-Grazing.shp'
    }
    
    # Simplified filenames for MapServer (without date)
    mapserver_filenames = {
        AffectedPopulation: 'impact_population.shp',
        ImpactedGDP: 'impact_gdp.shp',
        AffectedCrops: 'impact_crops.shp',
        AffectedRoads: 'impact_roads.shp',
        DisplacedPopulation: 'impact_displaced.shp',
        AffectedLivestock: 'impact_livestock.shp',
        AffectedGrazingLand: 'impact_grazing.shp'
    }
    
    field_mapping = {
        'gid_0': 'GID_0',
        'name_0': 'NAME_0',
        'name_1': 'NAME_1',
        'engtype_1': 'ENGTYPE_1',
        'lack_cc': 'LACK_CC',
        'cod': 'COD',
        'stock': 'stock',
        'flood_tot': 'flood_tot',
        'flood_perc': 'flood_perc',
        'geom': 'MULTIPOLYGON',
    }
    
    def handle(self, *args, **kwargs):
        """Main command handler"""
        try:
            os.makedirs(self.TEMP_DIR, exist_ok=True)
            
            # Ensure the MapServer directory exists
            os.makedirs(self.MAPSERVER_DIR, exist_ok=True)
            
            self.stdout.write(f"Using MapServer directory: {self.MAPSERVER_DIR}")
            self.sync_shapefiles()
            # Skip database loading - only save to files
            # self.load_shapefiles()
            self.copy_to_mapserver()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
        finally:
            self.cleanup_temp_files()
    
    def connect_sftp(self, host, port, username, password):
        """Establish an SFTP connection."""
        try:
            transport = paramiko.Transport((host, int(port)))
            transport.connect(username=username, password=password)
            return paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            raise Exception(f"Failed to connect to SFTP server: {str(e)}")

    def sync_shapefiles(self):
        """Download impact layer shapefiles from remote SFTP server with enhanced fallback mechanism."""
        sftp_host = config('SFTP_HOST')
        sftp_port = config('SFTP_PORT')
        sftp_username = config('SFTP_USERNAME')
        sftp_password = config('SFTP_PASSWORD')
        remote_folder_base = config('REMOTE_FOLDER_BASE')
        
        extensions = ['.shp', '.shx', '.dbf', '.prj']
        today = datetime.now()
        
        # Enhanced fallback - try up to 7 days back
        date_attempts = []
        for i in range(8):  # Today + 7 previous days
            check_date = today - timedelta(days=i)
            date_attempts.append(
                (check_date.strftime('%Y/%m/%d/00'), check_date.strftime('%Y%m%d'))
            )
        
        self.stdout.write("Connecting to SFTP server...")
        sftp = self.connect_sftp(sftp_host, sftp_port, sftp_username, sftp_password)
        
        try:
            for model, filename_template in self.model_configurations.items():
                base_filename_template = os.path.splitext(filename_template)[0]
                downloaded = False
                used_date = None  # Track which date was successfully used
                
                # Try today, then fallback to previous days
                for remote_folder, date_str in date_attempts:
                    if downloaded:
                        break  # Skip further attempts if already downloaded
                    
                    # Update filename with the current date being tried
                    base_filename = base_filename_template.replace(current_date, date_str)
                    remote_folder_path = f"{remote_folder_base}/{remote_folder}"
                    
                    self.stdout.write(f"Trying to download files for {date_str} from {remote_folder_path}...")
                    
                    try:
                        # Track if all critical files were downloaded
                        critical_files_found = True
                        
                        # Download all required extensions
                        for ext in extensions:
                            remote_file = f"{base_filename}{ext}"
                            local_path = os.path.join(self.TEMP_DIR, remote_file)
                            remote_path = os.path.join(remote_folder_path, remote_file).replace('\\', '/')
                            
                            try:
                                self.stdout.write(f"Downloading {remote_file}...")
                                sftp.get(remote_path, local_path)
                                
                                # Check if file is empty
                                if os.path.getsize(local_path) == 0:
                                    self.stdout.write(self.style.WARNING(f"Downloaded file {local_path} is empty"))
                                    if ext in ['.shp', '.shx', '.dbf']:
                                        critical_files_found = False
                                        break
                                else:
                                    self.stdout.write(self.style.SUCCESS(
                                        f"Downloaded {remote_file} to {local_path}"
                                    ))
                            
                            except FileNotFoundError:
                                self.stdout.write(self.style.WARNING(f"File {remote_file} not found at {remote_path}"))
                                if ext in ['.shp', '.shx', '.dbf']:
                                    critical_files_found = False
                                    break
                        
                        # If all critical files were found
                        if critical_files_found:
                            downloaded = True
                            used_date = date_str
                            # Update model_configurations with the full filename including .shp
                            self.model_configurations[model] = f"{base_filename}.shp"
                            self.stdout.write(self.style.SUCCESS(
                                f"Successfully downloaded all required files for {model.__name__} using data from {date_str}"
                            ))
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error downloading files for {date_str}: {str(e)}"))
                        # Continue to next date attempt
                
                # If we've tried all dates and still not downloaded
                if not downloaded:
                    # Check if we already have this layer in MapServer directory
                    mapserver_filename = self.mapserver_filenames[model]
                    mapserver_path = os.path.join(self.MAPSERVER_DIR, mapserver_filename)
                    if os.path.exists(mapserver_path):
                        self.stdout.write(self.style.WARNING(
                            f"Failed to download new data for {model.__name__}, but existing file exists in MapServer directory. "
                            f"Will continue using existing file: {mapserver_path}"
                        ))
                    else:
                        raise Exception(f"Failed to find data for {model.__name__} after checking {len(date_attempts)} days")
        
        finally:
            sftp.close()

    def load_shapefiles(self):
        """Load impact layer shapefiles into the database."""
        for model, filename in self.model_configurations.items():
            file_path = os.path.join(self.TEMP_DIR, filename)
            
            # Ensure the file exists
            if not os.path.exists(file_path):
                raise Exception(f"Shapefile not found at {file_path}")
            
            self.stdout.write(f"Loading data for {model.__name__} from {file_path}...")
            
            try:
                # Clear existing data
                model.objects.all().delete()
                
                # Load shapefile using LayerMapping
                lm = LayerMapping(
                    model, 
                    file_path, 
                    self.field_mapping,
                    transform=False,
                    encoding='iso-8859-1'
                )
                lm.save(strict=True, verbose=True)
                
                self.stdout.write(self.style.SUCCESS(
                    f"Data for {model.__name__} loaded successfully."
                ))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Full error: {str(e)}"))
                raise Exception(
                    f"Error loading data for {model.__name__}: {str(e)}"
                )

    def copy_to_mapserver(self):
        """Copy shapefiles to MapServer directory with consistent filenames and fallback to previous versions."""
        self.stdout.write(f"Copying shapefiles to MapServer directory: {self.MAPSERVER_DIR}")
        
        for model, original_filename in self.model_configurations.items():
            try:
                # Get base name without extension
                base_filename = os.path.splitext(original_filename)[0]
                
                # Get MapServer target filename
                mapserver_filename = self.mapserver_filenames[model]
                mapserver_base = os.path.splitext(mapserver_filename)[0]
                
                # Create a backup of existing files before overwriting
                extensions = ['.shp', '.shx', '.dbf', '.prj']
                backup_created = False
                
                # First, create backups of existing files if they exist
                for ext in extensions:
                    target_path = os.path.join(self.MAPSERVER_DIR, f"{mapserver_base}{ext}")
                    backup_path = os.path.join(self.MAPSERVER_DIR, f"{mapserver_base}_backup{ext}")
                    
                    if os.path.exists(target_path):
                        try:
                            shutil.copy2(target_path, backup_path)
                            backup_created = True
                            self.stdout.write(f"Created backup: {backup_path}")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Could not create backup of {target_path}: {str(e)}"))
                
                # Now copy new files
                successful_copy = True
                for ext in extensions:
                    source_path = os.path.join(self.TEMP_DIR, f"{base_filename}{ext}")
                    target_path = os.path.join(self.MAPSERVER_DIR, f"{mapserver_base}{ext}")
                    
                    # Check if source file exists before copying
                    if os.path.exists(source_path):
                        try:
                            shutil.copy2(source_path, target_path)
                            self.stdout.write(self.style.SUCCESS(
                                f"Copied {source_path} to {target_path}"
                            ))
                        except Exception as e:
                            successful_copy = False
                            self.stdout.write(self.style.ERROR(
                                f"Error copying {source_path} to {target_path}: {str(e)}"
                            ))
                            break
                    else:
                        # If critical file is missing
                        if ext in ['.shp', '.shx', '.dbf']:
                            successful_copy = False
                            self.stdout.write(self.style.WARNING(
                                f"Critical source file {source_path} does not exist, copy failed"
                            ))
                            break
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"Optional source file {source_path} does not exist, skipping"
                            ))
                
                # If copy failed and we have backups, restore them
                if not successful_copy and backup_created:
                    self.stdout.write(self.style.WARNING(
                        f"Copy failed for {model.__name__}, restoring from backup"
                    ))
                    for ext in extensions:
                        backup_path = os.path.join(self.MAPSERVER_DIR, f"{mapserver_base}_backup{ext}")
                        target_path = os.path.join(self.MAPSERVER_DIR, f"{mapserver_base}{ext}")
                        
                        if os.path.exists(backup_path):
                            try:
                                shutil.copy2(backup_path, target_path)
                                self.stdout.write(f"Restored {target_path} from backup")
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(
                                    f"Failed to restore {target_path} from backup: {str(e)}"
                                ))
                
                # Clean up backups if successful
                if successful_copy and backup_created:
                    for ext in extensions:
                        backup_path = os.path.join(self.MAPSERVER_DIR, f"{mapserver_base}_backup{ext}")
                        if os.path.exists(backup_path):
                            try:
                                os.remove(backup_path)
                                self.stdout.write(f"Removed backup: {backup_path}")
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(
                                    f"Could not remove backup {backup_path}: {str(e)}"
                                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Error handling MapServer files for {model.__name__}: {str(e)}"
                ))
                # Continue with next model instead of raising
                continue
    
    def cleanup_temp_files(self):
        """Clean up temporary files after processing."""
        self.stdout.write("Cleaning up temporary files...")
        if os.path.exists(self.TEMP_DIR):
            for filename in os.listdir(self.TEMP_DIR):
                file_path = os.path.join(self.TEMP_DIR, filename)
                try:
                    os.remove(file_path)
                    self.stdout.write(f"Removed {file_path}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"Error removing {file_path}: {e}"
                    ))
            try:
                os.rmdir(self.TEMP_DIR)
                self.stdout.write("Removed temporary directory")
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Error removing temporary directory: {e}"
                ))