import os
import shutil
from datetime import datetime, timedelta
import paramiko
from django.core.management.base import BaseCommand
from decouple import config

class Command(BaseCommand):
    help = 'Sync IBEW layer shapefiles from SFTP and save to directory structure'
    
    TEMP_DIR = './temp_ibew'
    IBEW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../CIMA_EAFW/flood_watch_system/data/shapefiles/ibew_shapefiles'))
    
    # IBEW layer types based on your extend_ibew_layers.py
    IBEW_LAYERS = [
        'healthtot',
        'popaff100', 
        'popaff25',
        'popafftot',
        'popage100',
        'popage25', 
        'popmob100',
        'popmob25'
    ]
    
    def handle(self, *args, **kwargs):
        try:
            os.makedirs(self.IBEW_DIR, exist_ok=True)
            self.stdout.write(f"Using IBEW directory: {self.IBEW_DIR}")
            self.sync_ibew_shapefiles()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
    
    def connect_sftp(self):
        try:
            host = config('SFTP_HOST')
            port = int(config('SFTP_PORT'))
            username = config('SFTP_USERNAME')
            password = config('SFTP_PASSWORD')
            
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)
            return paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            raise Exception(f"Failed to connect to SFTP: {str(e)}")

    def list_remote_directories(self, sftp, path):
        """List directories on remote SFTP server for debugging"""
        try:
            items = sftp.listdir(path)
            self.stdout.write(f"Contents of {path}: {items}")
            return items
        except Exception as e:
            self.stdout.write(f"Cannot list {path}: {str(e)}")
            return []

    def get_valid_ibew_path(self, sftp):
        """Try today's data first, then yesterday's data if needed"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        remote_base = config('IBEW_REMOTE_BASE', default='fp-eastafrica/storage/impact_assessment/fp_impact_forecast/nwp_multimodel-det/merged')
        
        # Check what's inside today's day directory
        day_path = f"{remote_base}/{today.strftime('%Y/%m/%d')}"
        day_contents = self.list_remote_directories(sftp, day_path)
        
        # First check today's data
        today_path = f"{remote_base}/{today.strftime('%Y/%m/%d/00')}"
        if self.check_remote_path_exists(sftp, today_path):
            self.stdout.write(self.style.SUCCESS(f"Using today's IBEW data from: {today.strftime('%Y-%m-%d')}"))
            return today_path, today, False
        
        # If no '00' subdirectory, try the day directory directly
        if day_contents:
            self.stdout.write(f"Using day directory directly: {day_path}")
            return day_path, today, False
        
        # Check yesterday
        yesterday_day_path = f"{remote_base}/{yesterday.strftime('%Y/%m/%d')}"
        yesterday_day_contents = self.list_remote_directories(sftp, yesterday_day_path)
        
        yesterday_path = f"{remote_base}/{yesterday.strftime('%Y/%m/%d/00')}"
        if self.check_remote_path_exists(sftp, yesterday_path):
            self.stdout.write(self.style.WARNING(
                f"Today's IBEW data not available. Using yesterday's data from: {yesterday.strftime('%Y-%m-%d')}"
            ))
            return yesterday_path, yesterday, True
        
        # If no '00' subdirectory for yesterday either, try yesterday day directory directly
        if yesterday_day_contents:
            self.stdout.write(f"Using yesterday's day directory directly: {yesterday_day_path}")
            return yesterday_day_path, yesterday, True
        
        # If both are missing, raise an error
        raise Exception("No IBEW data available for today or yesterday")

    def check_remote_path_exists(self, sftp, path):
        try:
            sftp.stat(path)
            return True
        except IOError:
            return False

    def sync_ibew_shapefiles(self):
        extensions = ['.shp', '.shx', '.dbf', '.prj']
        
        sftp = self.connect_sftp()
        
        try:
            # Get valid IBEW path with fallback to yesterday
            ibew_path, data_date, is_fallback = self.get_valid_ibew_path(sftp)
            date_str = data_date.strftime('%Y%m%d')
            
            # Create date directory for direct download
            date_dir = os.path.join(self.IBEW_DIR, date_str)
            os.makedirs(date_dir, exist_ok=True)
            
            # Download IBEW shapefiles directly to target directory
            self.stdout.write(f"Downloading IBEW shapefiles directly to {date_dir}...")
            for layer_type in self.IBEW_LAYERS:
                base_filename = f"{date_str}0000_FPimpacts-{layer_type}"
                downloaded = False
                
                try:
                    all_files_found = True
                    
                    for ext in extensions:
                        remote_file = f"{base_filename}{ext}"
                        local_path = os.path.join(date_dir, remote_file)
                        remote_file_path = f"{ibew_path}/{remote_file}".replace('\\', '/')
                        
                        try:
                            sftp.get(remote_file_path, local_path)
                            if os.path.getsize(local_path) == 0:
                                self.stdout.write(self.style.WARNING(f"Downloaded file {local_path} is empty"))
                                all_files_found = False
                                break
                            else:
                                self.stdout.write(self.style.SUCCESS(f"Downloaded {remote_file} to {date_dir}"))
                        except FileNotFoundError:
                            self.stdout.write(self.style.WARNING(f"File not found: {remote_file_path}"))
                            if ext in ['.shp', '.shx', '.dbf']:
                                all_files_found = False
                                break
                    
                    if all_files_found:
                        downloaded = True
                        self.stdout.write(self.style.SUCCESS(f"Downloaded {layer_type} for {date_str}"))
                
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error downloading {layer_type}: {str(e)}"))
                
                if not downloaded:
                    self.stdout.write(self.style.WARNING(f"Failed to download {layer_type}"))
        
        finally:
            sftp.close()

