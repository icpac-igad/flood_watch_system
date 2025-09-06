import os
from datetime import datetime
import paramiko
from decouple import config
from django.core.management.base import BaseCommand
import rasterio
import numpy as np

class Command(BaseCommand):
    help = 'Sync remote raster data from SFTP, merge and process it locally using rasterio'

    RASTER_DIR = './temp_rasters'

    raster_groups = {
        "Group 1": ["group1_mosaic_alert_level.tif"],  # Group 1 raster
        "Group 2": ["group2_mosaic_alert_level.tif"],  # Group 2 raster
        "Group 4": ["group4_mosaic_alert_level.tif"],  # Group 4 raster
    }

    def handle(self, *args, **kwargs):
        """Main command handler"""
        try:
            os.makedirs(self.RASTER_DIR, exist_ok=True)
            self.sync_rasters()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
        finally:
            self.cleanup_temp_files(preserve_merged=True)

    def connect_sftp(self, host, port, username, password):
        """Establish an SFTP connection."""
        try:
            transport = paramiko.Transport((host, int(port)))
            transport.connect(username=username, password=password)
            return paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            raise Exception(f"Failed to connect to SFTP server: {str(e)}")

    def sync_rasters(self):
        """Download raster files from remote SFTP server."""
        sftp_host = config('SFTP_HOST')
        sftp_port = config('SFTP_PORT')
        sftp_username = config('SFTP_USERNAME')
        sftp_password = config('SFTP_PASSWORD')
        remote_folder_base = config('REMOTE_FOLDER_BASE')

        remote_date = datetime.now().strftime('%Y/%m/%d/00/0000')
        remote_folder = f"{remote_folder_base}/{remote_date}/HMC"

        self.stdout.write("Connecting to SFTP server...")
        sftp = self.connect_sftp(sftp_host, sftp_port, sftp_username, sftp_password)

        try:
            for group, filenames in self.raster_groups.items():
                self.stdout.write(f"Processing {group}...")
                local_group_dir = os.path.join(self.RASTER_DIR, group)
                os.makedirs(local_group_dir, exist_ok=True)

                # Download the raster files for this group
                local_files = []
                for filename in filenames:
                    remote_file = os.path.join(remote_folder, filename).replace('\\', '/')
                    local_file = os.path.join(local_group_dir, filename)
                    self.stdout.write(f"Downloading {filename}...")
                    try:
                        sftp.get(remote_file, local_file)
                        local_files.append(local_file)
                        self.stdout.write(self.style.SUCCESS(f"Downloaded {filename}"))
                    except FileNotFoundError:
                        self.stdout.write(self.style.WARNING(f"{filename} not found at {remote_file}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error downloading {filename}: {str(e)}"))

                # Merge the rasters for this group if files were downloaded
                if local_files:
                    self.merge_rasters(local_files, local_group_dir)

        finally:
            sftp.close()

    def merge_rasters(self, raster_files, output_dir):
        """Merge raster files and save them to the output directory using rasterio."""
        self.stdout.write("Merging raster files using rasterio...")
        try:
            # First, read and store all raster data and metadata
            raster_data = []
            for raster in raster_files:
                with rasterio.open(raster) as src:
                    # Read all bands
                    data = src.read()
                    profile = src.profile.copy()
                    transform = src.transform
                    crs = src.crs
                    
                    # Handle negative pixel height
                    if transform[4] == 0 and transform[5] > 0:
                        # Flip all bands
                        data = np.flip(data, axis=1)
                        # Adjust the transform
                        ulx = transform[2]
                        uly = transform[5] + (data.shape[1] * abs(transform[4]))
                        transform = rasterio.Affine(
                            transform[0],
                            0.0,
                            ulx,
                            0.0,
                            -abs(transform[4]),
                            uly
                        )
                    
                    raster_data.append({
                        'data': data,
                        'profile': profile,
                        'transform': transform,
                        'crs': crs
                    })

            # If we have rasters to merge
            if raster_data:
                # Create output profile from the first raster
                out_profile = raster_data[0]['profile']
                
                # Update output profile for merged result
                out_profile.update({
                    'height': raster_data[0]['data'].shape[1],
                    'width': raster_data[0]['data'].shape[2],
                    'transform': raster_data[0]['transform'],
                    'crs': raster_data[0]['crs'],
                    'compress': 'lzw',
                    'tiled': True,
                    'blockxsize': 256,
                    'blockysize': 256,
                    'driver': 'GTiff'
                })

                # Define output path
                merged_filename = f"merged_{datetime.now().strftime('%Y%m%d%H%M%S')}.tif"
                merged_file_path = os.path.join(output_dir, merged_filename)

                # Write the merged raster
                with rasterio.open(merged_file_path, 'w', **out_profile) as dst:
                    # Write each band from each raster
                    for band_idx in range(raster_data[0]['data'].shape[0]):
                        band_data = np.zeros((out_profile['height'], out_profile['width']), 
                                           dtype=raster_data[0]['data'].dtype)
                        
                        # Combine data from all rasters for this band
                        for raster in raster_data:
                            # Only write non-zero/non-nodata values
                            mask = raster['data'][band_idx] != 0
                            band_data[mask] = raster['data'][band_idx][mask]
                        
                        dst.write(band_data, band_idx + 1)

                self.stdout.write(self.style.SUCCESS(f"Merged raster saved to {merged_file_path}"))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error merging rasters with rasterio: {e}"))
            raise

    def cleanup_temp_files(self, preserve_merged=True):
        """Clean up temporary files after processing, optionally preserving merged files."""
        self.stdout.write("Cleaning up temporary files...")
        merged_files = []
        if os.path.exists(self.RASTER_DIR):
            for group_dir in os.listdir(self.RASTER_DIR):
                group_dir_path = os.path.join(self.RASTER_DIR, group_dir)
                if os.path.isdir(group_dir_path):
                    for filename in os.listdir(group_dir_path):
                     file_path = os.path.join(group_dir_path, filename)
                     if filename.startswith('merged_'):
                        # Move merged file to the main RASTER_DIR
                        new_path = os.path.join(self.RASTER_DIR, filename)
                        os.rename(file_path, new_path)
                        merged_files.append(new_path)
                        self.stdout.write(f"Preserved merged file: {filename}")

    # Then clean up all group directories and their contents
        if os.path.exists(self.RASTER_DIR):
            for group_dir in os.listdir(self.RASTER_DIR):
                group_dir_path = os.path.join(self.RASTER_DIR, group_dir)
                if os.path.isdir(group_dir_path):
                    for filename in os.listdir(group_dir_path):
                        file_path = os.path.join(group_dir_path, filename)
                        try:
                            os.remove(file_path)
                            self.stdout.write(f"Removed {file_path}")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error removing {file_path}: {e}"))
                
                # Remove the group directory
                    try:
                        os.rmdir(group_dir_path)
                        self.stdout.write(f"Removed group directory {group_dir_path}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Error removing group directory: {e}"))
    
        self.stdout.write(self.style.SUCCESS(f"Cleanup completed. Preserved {len(merged_files)} merged files."))