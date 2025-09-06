import os
import paramiko
import shutil
import traceback
import tempfile
import glob
from datetime import datetime, timedelta
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from django.conf import settings

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))

def config(key, default=None):
    return os.environ.get(key, default)

class Command(BaseCommand):
    help = 'Sync TIFF files from SFTP server and update MapServer raster files'
    
    def __init__(self):
        super().__init__()
        self.current_date = datetime.now()
        self.sftp = None
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'temp_rasters')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # MapServer configuration - adapt to your project structure
        base_dir = getattr(settings, 'BASE_DIR', None)
        if base_dir:
            # Local development path - now using data/rasters in project root
            default_raster_dir = os.path.join(base_dir, '..', '..', 'data', 'rasters')
            # Make it absolute
            default_raster_dir = os.path.abspath(default_raster_dir)
        else:
            default_raster_dir = '/etc/mapserver/data/rasters'
            
        self.mapserver_raster_dir = config('MAPSERVER_RASTER_DIR', default=default_raster_dir)
        
        # Group configuration
        self.groups = ['Group 1', 'Group 2', 'Group 4']
        self.preserve_merged = True  # Set to False to clean up all temp files
        
    def handle(self, *args, **options):
        """Main command handler"""
        # Ensure MapServer raster directory exists
        try:
            os.makedirs(self.mapserver_raster_dir, exist_ok=True)
            self.stdout.write(self.style.SUCCESS(f"MapServer raster directory: {self.mapserver_raster_dir}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to create MapServer raster directory: {str(e)}"))
            self.stderr.write(self.style.ERROR(f"Please check permissions or create it manually"))
            return
        
        self.stdout.write("Connecting to SFTP server...")
        try:
            self.sftp = self.connect_sftp()
            
            # Try with current date first
            current_date_success = self.process_date(self.current_date)
            
            # If current date fails, try with yesterday's date
            if not current_date_success:
                yesterday = self.current_date - timedelta(days=1)
                self.stdout.write(self.style.WARNING(f"Today's data not available. Trying yesterday ({yesterday.strftime('%Y-%m-%d')})..."))
                yesterday_success = self.process_date(yesterday)
                
                if not yesterday_success:
                    self.stdout.write(self.style.ERROR("Could not find data for either today or yesterday."))
                    
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {str(e)}"))
            traceback.print_exc()
        finally:
            if self.sftp:
                self.sftp.close()
            self.cleanup()
        
    def connect_sftp(self):
        """Connect to SFTP server"""
        try:
            transport = paramiko.Transport((
                config('SFTP_HOST'),
                int(config('SFTP_PORT', default=22))
            ))
            transport.connect(
                username=config('SFTP_USERNAME'),
                password=config('SFTP_PASSWORD')
            )
            return paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            raise Exception(f"Failed to connect to SFTP server: {str(e)}")
    
    def process_date(self, date):
        """Process files for a specific date"""
        date_str = date.strftime('%Y/%m/%d')
        sftp_base_path = config('REMOTE_FOLDER_BASE', default='fp-eastafrica/storage/impact_assessment/fp_impact_forecast/nwp_gfs-det')
        path_pattern = f"{sftp_base_path}/{date_str}/00/0000"
        
        # Create date-specific directory
        date_raster_dir = os.path.join(self.mapserver_raster_dir, date.strftime('%Y%m%d'))
        os.makedirs(date_raster_dir, exist_ok=True)
        
        try:
            # Check if the directory exists
            try:
                self.sftp.stat(path_pattern)
            except IOError:
                self.stdout.write(self.style.WARNING(f"Directory not found: {path_pattern}"))
                return False
            
            # Process flood hazard file
            flood_hazard_file = f"flood_hazard_map_floodproofs_{date.strftime('%Y%m%d')}0000.tif"
            flood_remote_path = f"{path_pattern}/{flood_hazard_file}"
            flood_local_path = os.path.join(self.temp_dir, flood_hazard_file)
            
            flood_downloaded = False
            try:
                # Check if flood hazard file exists
                self.sftp.stat(flood_remote_path)
                
                # Download the flood hazard file
                self.stdout.write(f"Downloading {flood_hazard_file}...")
                self.sftp.get(flood_remote_path, flood_local_path)
                self.stdout.write(self.style.SUCCESS(f"Downloaded flood hazard map to {flood_local_path}"))
                flood_downloaded = True
                
                # Copy to date-specific MapServer directory with proper naming
                flood_target = os.path.join(date_raster_dir, f"flood_hazard_{date.strftime('%Y%m%d')}.tif")
                flood_latest = os.path.join(date_raster_dir, "flood_hazard_latest.tif")
                
                shutil.copy2(flood_local_path, flood_target)
                self.stdout.write(self.style.SUCCESS(f"Copied flood hazard map to {flood_target}"))
                
                # Update latest symlink or copy if symlinks not supported
                if os.path.exists(flood_latest) or os.path.islink(flood_latest):
                    os.remove(flood_latest)
                
                try:
                    # Use relative path for symlink to ensure portability between environments
                    os.symlink(os.path.basename(flood_target), flood_latest)
                    self.stdout.write(self.style.SUCCESS(f"Created symlink for flood_hazard_latest.tif"))
                except (OSError, AttributeError):
                    # Fallback for Windows or systems without symlink support
                    shutil.copy2(flood_target, flood_latest)
                    self.stdout.write(self.style.SUCCESS(f"Copied file as flood_hazard_latest.tif"))
                
            except IOError as e:
                self.stdout.write(self.style.WARNING(f"{flood_hazard_file} not found at {flood_remote_path}"))
            
            # Process group alert files
            hmc_path = f"{path_pattern}/HMC"
            try:
                self.sftp.stat(hmc_path)
            except IOError:
                self.stdout.write(self.style.WARNING(f"HMC directory not found: {hmc_path}"))
                # Return True if at least the flood hazard file was processed
                return flood_downloaded
            
            # Process each group and save separately
            alert_files_downloaded = []
            
            for group_name in self.groups:
                group_dir = os.path.join(self.temp_dir, group_name)
                os.makedirs(group_dir, exist_ok=True)
                
                self.stdout.write(f"Processing {group_name}...")
                group_file = f"{group_name.lower().replace(' ', '')}_mosaic_alert_level.tif"
                group_remote_path = f"{hmc_path}/{group_file}"
                group_local_path = os.path.join(group_dir, group_file)
                
                try:
                    # Check if file exists
                    try:
                        self.sftp.stat(group_remote_path)
                    except IOError:
                        self.stdout.write(self.style.WARNING(f"{group_file} not found at {group_remote_path}"))
                        continue
                    
                    # Download the group alert file
                    self.stdout.write(f"Downloading {group_file}...")
                    self.sftp.get(group_remote_path, group_local_path)
                    self.stdout.write(self.style.SUCCESS(f"Downloaded {group_file} to {group_local_path}"))
                    alert_files_downloaded.append(group_local_path)
                    
                    # Save individual group alert files separately in date directory
                    group_target = os.path.join(date_raster_dir, f"{group_name.lower().replace(' ', '')}_alert_{date.strftime('%Y%m%d')}.tif")
                    shutil.copy2(group_local_path, group_target)
                    self.stdout.write(self.style.SUCCESS(f"Copied {group_name} alert to {group_target}"))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing {group_name}: {str(e)}"))
            
            # Don't merge alert files - save them separately
            # Merge alert files if any were downloaded
            if alert_files_downloaded:
                merged_alerts_file = self.merge_alert_files(alert_files_downloaded, date)
                if merged_alerts_file:
                    # Copy to date-specific MapServer directory
                    alerts_target = os.path.join(date_raster_dir, f"alerts_{date.strftime('%Y%m%d')}.tif")
                    alerts_latest = os.path.join(date_raster_dir, "alerts_latest.tif")
                    
                    shutil.copy2(merged_alerts_file, alerts_target)
                    self.stdout.write(self.style.SUCCESS(f"Copied merged alerts to {alerts_target}"))
                    
                    # Update latest symlink
                    if os.path.exists(alerts_latest) or os.path.islink(alerts_latest):
                        os.remove(alerts_latest)
                    
                    try:
                        # Use relative path for symlink to ensure portability
                        os.symlink(os.path.basename(alerts_target), alerts_latest)
                        self.stdout.write(self.style.SUCCESS(f"Created symlink for alerts_latest.tif"))
                    except (OSError, AttributeError):
                        # Fallback for Windows or systems without symlink support
                        shutil.copy2(alerts_target, alerts_latest)
                        self.stdout.write(self.style.SUCCESS(f"Copied file as alerts_latest.tif"))
            
            # Return True if either flood hazard or any alert files were processed
            return flood_downloaded or bool(alert_files_downloaded)
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing date {date.strftime('%Y-%m-%d')}: {str(e)}"))
            traceback.print_exc()
            return False
    
    def merge_alert_files(self, alert_files, date):
        """Merge alert files using GDAL"""
        if not alert_files:
            return None
        
        self.stdout.write(f"Merging {len(alert_files)} alert files...")
        
        try:
            # Import GDAL only when needed
            try:
                from osgeo import gdal
                GDAL_AVAILABLE = True
            except ImportError:
                GDAL_AVAILABLE = False
                self.stdout.write(self.style.WARNING("GDAL not available for merging. Trying alternative method."))
            
            merged_file = os.path.join(self.temp_dir, f"merged_alerts_{date.strftime('%Y%m%d')}.tif")
            
            if GDAL_AVAILABLE:
                # Create VRT
                vrt_file = os.path.join(self.temp_dir, f"merged_alerts_{date.strftime('%Y%m%d')}.vrt")
                vrt_options = gdal.BuildVRTOptions(resampleAlg='nearest', separate=False)
                vrt = gdal.BuildVRT(vrt_file, alert_files, options=vrt_options)
                
                # Create GeoTIFF from VRT
                gdal.Translate(merged_file, vrt, options=gdal.TranslateOptions(
                    format='GTiff',
                    creationOptions=['COMPRESS=LZW']
                ))
                
                self.stdout.write(self.style.SUCCESS(f"Successfully merged alert files to {merged_file}"))
                return merged_file
            else:
                # Fallback - just use the first alert file
                shutil.copy2(alert_files[0], merged_file)
                self.stdout.write(self.style.WARNING(f"GDAL not available. Using first alert file as merged file: {merged_file}"))
                return merged_file
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error merging alert files: {str(e)}"))
            traceback.print_exc()
            
            # Fallback - just use the first alert file
            try:
                merged_file = os.path.join(self.temp_dir, f"merged_alerts_{date.strftime('%Y%m%d')}.tif")
                shutil.copy2(alert_files[0], merged_file)
                self.stdout.write(self.style.WARNING(f"Using first alert file as merged file due to error: {merged_file}"))
                return merged_file
            except Exception as copy_error:
                self.stderr.write(self.style.ERROR(f"Failed to use fallback method: {str(copy_error)}"))
                return None
    
    def cleanup(self):
        """Clean up temporary files"""
        self.stdout.write("Cleaning up temporary files...")
        
        # Find merged files
        merged_files = glob.glob(os.path.join(self.temp_dir, "merged_alerts_*.tif"))
        
        # Remove all group directories
        for group_name in self.groups:
            group_dir = os.path.join(self.temp_dir, group_name)
            if os.path.exists(group_dir):
                for file in os.listdir(group_dir):
                    file_path = os.path.join(group_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            self.stdout.write(f"Removed {file_path}")
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"Error removing {file_path}: {str(e)}"))
                
                try:
                    os.rmdir(group_dir)
                    self.stdout.write(f"Removed group directory {group_dir}")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error removing directory {group_dir}: {str(e)}"))
        
        # Clean up flood hazard files
        for file in glob.glob(os.path.join(self.temp_dir, "flood_hazard_*.tif")):
            try:
                os.remove(file)
                self.stdout.write(f"Removed {file}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error removing {file}: {str(e)}"))
        
        # If not preserving merged files, remove them too
        if not self.preserve_merged:
            for file in merged_files:
                try:
                    os.remove(file)
                    self.stdout.write(f"Removed merged file {file}")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error removing {file}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Cleanup completed. Preserved {len(merged_files)} merged files."))
