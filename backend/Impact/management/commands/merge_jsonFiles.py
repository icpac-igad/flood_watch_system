import os
import json
import shutil
from datetime import datetime, timedelta
import paramiko
import geopandas as gpd
from django.core.management.base import BaseCommand
from decouple import config
import tempfile

class Command(BaseCommand):
    help = 'Download and process remote JSON and shapefile data from an SFTP server.'

    def get_data_path(self, base_date=None):
        if base_date is None:
            base_date = datetime.now()
        year = str(base_date.year)
        month = str(base_date.month).zfill(2)
        day = str(base_date.day).zfill(2)
        
        json_remote_dir = config('JSON_REMOTE_DIR').rstrip('/')
        
        base_path = f"{json_remote_dir}/{year}/{month}/{day}"
        full_path = f"{base_path}/00"
        
        return base_path, full_path, base_date

    def get_output_dir(self):
        # Use environment variable for timeseries data directory
        timeseries_dir = config('TIMESERIES_OUTPUT_DIR', default='/etc/mapserver/data/timeseries_data')
        is_shared_volume = True
        
        if not os.path.exists(timeseries_dir):
            try:
                os.makedirs(timeseries_dir)
                self.stdout.write(self.style.SUCCESS(f"Created timeseries directory: {timeseries_dir}"))
            except Exception as e:
                raise Exception(f"Could not create {timeseries_dir}: {e}. Check permissions or volume mounting.")
        
        try:
            # Verify writability
            test_file = os.path.join(timeseries_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            self.stdout.write(self.style.SUCCESS(f"Using writable timeseries directory: {timeseries_dir}"))
        except (IOError, PermissionError) as e:
            raise Exception(f"Timeseries directory {timeseries_dir} not writable: {e}. Ensure permissions and volume are correctly configured.")
        
        return timeseries_dir, is_shared_volume

    def check_remote_path_exists(self, sftp, path):
        try:
            sftp.stat(path)
            return True
        except IOError:
            return False

    def get_valid_json_path(self, sftp):
        """Try today's data first, then yesterday's data if needed"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # First check today's data
        _, today_path, _ = self.get_data_path(today)
        if self.check_remote_path_exists(sftp, today_path):
            self.stdout.write(self.style.SUCCESS(f"Using today's data from: {today.strftime('%Y-%m-%d')}"))
            return today_path, today, False
        
        # If today's data not available, try yesterday's
        _, yesterday_path, _ = self.get_data_path(yesterday)
        if self.check_remote_path_exists(sftp, yesterday_path):
            self.stdout.write(self.style.WARNING(
                f"Today's data not available. Using yesterday's data from: {yesterday.strftime('%Y-%m-%d')}"
            ))
            return yesterday_path, yesterday, True
        
        # If both are missing, raise an error
        raise Exception("No data available for today or yesterday")

    def handle(self, *args, **kwargs):
        try:
            # Get the output directory
            output_dir, is_shared_volume = self.get_output_dir()
            output_file = os.path.join(output_dir, 'merged_data.geojson')
            self.stdout.write(self.style.SUCCESS(f"Will save to: {output_file} (Timeseries directory: {is_shared_volume})"))
            
            # Create temporary directory for processing intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                json_dir = os.path.join(temp_dir, 'json_files')
                shapefile_dir = os.path.join(temp_dir, 'shapefiles')
                os.makedirs(json_dir, exist_ok=True)
                os.makedirs(shapefile_dir, exist_ok=True)
                
                # Sync data from SFTP server to temp directory
                json_files, shapefile_dir, data_date, is_fallback = self.sync_data(json_dir, shapefile_dir)
                
                # Process and merge data, saving to the timeseries directory
                self.process_and_merge_data(json_files, shapefile_dir, output_file, data_date, is_fallback)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
            raise

    def connect_sftp(self):
        hostname = config('SFTP_HOST')
        port = int(config('SFTP_PORT'))
        username = config('SFTP_USERNAME')
        password = config('SFTP_PASSWORD')

        try:
            transport = paramiko.Transport((hostname, port))
            transport.connect(username=username, password=password)
            return paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            raise Exception(f"Failed to connect to SFTP server: {e}")

    def sync_data(self, json_dir, shapefile_dir):
        sftp = self.connect_sftp()

        try:
            # Get valid JSON path with fallback to yesterday
            json_path, data_date, is_fallback = self.get_valid_json_path(sftp)

            # Get static shapefile directory
            shapefile_remote_dir = config('SHAPEFILE_REMOTE_DIR')
            if not self.check_remote_path_exists(sftp, shapefile_remote_dir):
                raise Exception(f"Shapefile directory not found: {shapefile_remote_dir}")

            # Download JSON files
            self.stdout.write("Downloading JSON files...")
            json_files = self.download_files(sftp, json_path, json_dir, '.json')

            # Download shapefiles
            self.stdout.write("Downloading shapefiles...")
            shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj']
            self.download_files(sftp, shapefile_remote_dir, shapefile_dir, extensions=shapefile_extensions)

            return json_files, shapefile_dir, data_date, is_fallback

        finally:
            sftp.close()

    def download_files(self, sftp, remote_dir, local_dir, extensions):
        try:
            remote_files = sftp.listdir(remote_dir)
        except IOError as e:
            raise Exception(f"Error accessing remote directory {remote_dir}: {e}")

        downloaded_files = []

        for file in remote_files:
            if isinstance(extensions, str):
                valid = file.endswith(extensions)
            else:
                valid = any(file.endswith(ext) for ext in extensions)

            if valid:
                remote_path = os.path.join(remote_dir, file).replace('\\', '/')
                local_path = os.path.join(local_dir, file)

                try:
                    sftp.get(remote_path, local_path)
                    downloaded_files.append(local_path)
                    self.stdout.write(self.style.SUCCESS(f"Downloaded {file}"))
                except FileNotFoundError:
                    self.stderr.write(self.style.WARNING(f"File not found: {remote_path}"))
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"Error downloading {file}: {e}"))

        if not downloaded_files:
            raise Exception(f"No files with extensions {extensions} found in {remote_dir}")

        return downloaded_files

    def process_and_merge_data(self, json_files, shapefile_dir, output_file, data_date, is_fallback):
        try:
            # Ensure the output directory exists and is writable
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self.stdout.write(self.style.SUCCESS(f"Created output directory: {output_dir}"))
            
            # Test if the directory is writable
            test_file = os.path.join(output_dir, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                self.stdout.write(self.style.SUCCESS(f"Directory {output_dir} is writable"))
            except (IOError, PermissionError) as e:
                raise Exception(f"Cannot write to {output_dir}: {e}. Ensure permissions are correct.")

            # Find the shapefile
            shapefile_path = next(
                (os.path.join(shapefile_dir, f) for f in os.listdir(shapefile_dir) if f.endswith('.shp')), None
            )

            if not shapefile_path:
                raise FileNotFoundError("No .shp file found in the specified directory.")

            gdf = gpd.read_file(shapefile_path)

            if gdf.crs is None:
                self.stdout.write(self.style.WARNING("Warning: CRS missing. Setting CRS to EPSG:4326."))
                gdf.set_crs('EPSG:4326', allow_override=True, inplace=True)

            merged_data = []

            for json_file in json_files:
                try:
                    with open(json_file, 'r') as file:
                        data = json.load(file)
                        if isinstance(data, str):
                            data = json.loads(data)
                        if not isinstance(data, (list, dict)):
                            raise ValueError(f"Invalid JSON format in {json_file}")
                        
                        if isinstance(data, dict):
                            data = [data]

                        for entry in data:
                            if not isinstance(entry, dict):
                                self.stdout.write(self.style.WARNING(
                                    f"Skipping invalid entry in {json_file}: {entry}"
                                ))
                                continue
                                
                            section_name = entry.get('section_name')
                            if section_name:
                                match = gdf[gdf['SEC_NAME'] == section_name]
                                if not match.empty:
                                    merged_entry = entry.copy()
                                    # Add data date and fallback flag
                                    merged_entry['data_date'] = data_date.strftime('%Y-%m-%d')
                                    merged_entry['is_fallback'] = is_fallback
                                    
                                    for col in match.columns:
                                        if col != 'geometry':
                                            merged_entry[col] = match.iloc[0][col]
                                    merged_entry['geometry'] = match.iloc[0].geometry
                                    merged_data.append(merged_entry)
                                else:
                                    self.stdout.write(self.style.WARNING(
                                        f"No match for section_name: {section_name}"
                                    ))
                except json.JSONDecodeError as e:
                    self.stderr.write(self.style.WARNING(
                        f"Error parsing JSON file {json_file}: {e}"
                    ))
                except Exception as e:
                    self.stderr.write(self.style.WARNING(
                        f"Error processing file {json_file}: {e}"
                    ))

            if merged_data:
                # Create the GeoDataFrame
                final_gdf = gpd.GeoDataFrame(merged_data, geometry='geometry')
                final_gdf.set_crs(epsg=4326, inplace=True)
                
                # Add metadata about the data date and fallback status
                final_gdf.attrs['data_date'] = data_date.strftime('%Y-%m-%d')
                final_gdf.attrs['is_fallback'] = is_fallback
                
                # Log a warning if using fallback data
                if is_fallback:
                    self.stdout.write(self.style.WARNING(
                        f"Using yesterday's data as fallback. Data date: {data_date.strftime('%Y-%m-%d')}"
                    ))
                
                # Save to the output file
                if os.path.exists(output_file):
                    os.remove(output_file)
                
                final_gdf.to_file(output_file, driver='GeoJSON')
                self.stdout.write(self.style.SUCCESS(f"Merged GeoJSON saved at {output_file}"))
            else:
                self.stdout.write(self.style.WARNING("No data to merge."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error merging data: {e}"))
            raise