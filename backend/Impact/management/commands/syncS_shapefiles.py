import os
from io import BytesIO
import paramiko
from datetime import datetime
import geopandas as gpd
import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from decouple import config
from Impact.models import SectorData

class Command(BaseCommand):
    help = 'Sync remote sector shapefiles from SFTP and upload to database'
    
    SHAPEFILE_DIR = './temp_shapefiles'
    SECTOR_FILENAME = 'fp_sections_igad.shp'
    
    # Updated field mapping with correct geometry type
    field_mapping = {
        'sec_code': 'SEC_CODE',
        'sec_name': 'SEC_NAME',
        'basin': 'BASIN',
        'domain': 'DOMAIN',
        'admin_b_l1': 'ADMIN_B_L1',
        'admin_b_l2': 'ADMIN_B_L2',
        'admin_b_l3': 'ADMIN_B_L3',
        'sec_rs': 'SEC_RS',
        'area': 'AREA',
        'lat': 'LAT',
        'lon': 'LON',
        'q_thr1': 'Q_THR1',
        'q_thr2': 'Q_THR2',
        'q_thr3': 'Q_THR3',
        'cat': 'cat',
        'id': 'ID',
        'geom': 'POINT'  # Changed back to 'POINT' to match Django's geometry field type
    }
    
    def handle(self, *args, **kwargs):
        """Main command handler"""
        try:
            os.makedirs(self.SHAPEFILE_DIR, exist_ok=True)
            self.sync_sector_shapefile()
            self.load_sector_data()
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

    def sync_sector_shapefile(self):
        """Download sector shapefile from remote SFTP server."""
        sftp_host = config('SFTP_HOST')
        sftp_port = config('SFTP_PORT')
        sftp_username = config('SFTP_USERNAME')
        sftp_password = config('SFTP_PASSWORD')
        sectors_remote_folder = config('SHAPEFILE_REMOTE_DIR')
        
        extensions = ['.shp', '.shx', '.dbf', '.prj']
        base_filename = os.path.splitext(self.SECTOR_FILENAME)[0]
        
        self.stdout.write("Connecting to SFTP server...")
        sftp = self.connect_sftp(sftp_host, sftp_port, sftp_username, sftp_password)
        
        try:
            for ext in extensions:
                remote_file = f"{base_filename}{ext}"
                local_path = os.path.join(self.SHAPEFILE_DIR, remote_file)
                remote_path = os.path.join(sectors_remote_folder, remote_file).replace('\\', '/')
                
                try:
                    self.stdout.write(f"Downloading {remote_file}...")
                    sftp.get(remote_path, local_path)
                    self.stdout.write(self.style.SUCCESS(
                        f"Downloaded {remote_file} to {local_path}"
                    ))
                except FileNotFoundError:
                    msg = f"Warning: {remote_file} not found at {remote_path}"
                    if ext in ['.shp', '.shx', '.dbf']:
                        raise Exception(msg)
                    else:
                        self.stdout.write(self.style.WARNING(msg))
        finally:
            sftp.close()

    def load_sector_data(self):
        """Load sector data into the database using LayerMapping."""
        file_path = os.path.join(self.SHAPEFILE_DIR, self.SECTOR_FILENAME)
        
        self.stdout.write(f"Loading sector data from {file_path}...")
        
        try:
            # Clear existing data
            SectorData.objects.all().delete()
            
            # Debug output for shapefile structure
            gdf = gpd.read_file(file_path)
            self.stdout.write(f"Columns in shapefile: {gdf.columns.tolist()}")
            self.stdout.write(f"First row data: {gdf.iloc[0].to_dict()}")
            
            # Use LayerMapping to load the data
            lm = LayerMapping(
                SectorData,
                file_path,
                self.field_mapping,
                transform=True,  # Added transform=True to ensure proper coordinate transformation
                encoding='iso-8859-1'
            )
            lm.save(strict=True, verbose=True)
            
            self.stdout.write(self.style.SUCCESS(
                f"Successfully loaded sectors into database."
            ))
            
        except Exception as e:
            raise Exception(f"Error loading sector data: {str(e)}")
    
    def cleanup_temp_files(self):
        """Clean up temporary files after processing."""
        self.stdout.write("Cleaning up temporary files...")
        if os.path.exists(self.SHAPEFILE_DIR):
            for filename in os.listdir(self.SHAPEFILE_DIR):
                file_path = os.path.join(self.SHAPEFILE_DIR, filename)
                try:
                    os.remove(file_path)
                    self.stdout.write(f"Removed {file_path}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"Error removing {file_path}: {e}"
                    ))
            try:
                os.rmdir(self.SHAPEFILE_DIR)
                self.stdout.write("Removed temporary directory")
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Error removing temporary directory: {e}"
                ))