"""
Unified Django management command to load all static geographic data (Admin1, Admin2, Lakes, Rivers, MonitoringStations)
This single script handles all static data ingestion for the FloodWatch system.
"""

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, Point
from django.contrib.gis.gdal import DataSource
from django.db import transaction
from Impact.models import Admin0, Admin1, Admin2, WaterBodies, MonitoringStation, HydroRivers, EnsembleControlPoint
import json
import os
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load all static geographic data (Admin1, Admin2, Lakes, Rivers, MonitoringStations) from static files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='/app/static',
            help='Directory containing the data files (default: /app/static)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run without saving to database'
        )
        parser.add_argument(
            '--skip-admin0',
            action='store_true',
            help='Skip loading Admin0 (country) data'
        )
        parser.add_argument(
            '--skip-admin1',
            action='store_true',
            help='Skip loading Admin1 data'
        )
        parser.add_argument(
            '--skip-admin2',
            action='store_true',
            help='Skip loading Admin2 data'
        )
        parser.add_argument(
            '--skip-lakes',
            action='store_true',
            help='Skip loading Lakes data'
        )
        parser.add_argument(
            '--skip-rivers',
            action='store_true',
            help='Skip loading HydroRIVERS data'
        )
        parser.add_argument(
            '--skip-stations',
            action='store_true',
            help='Skip loading MonitoringStation data'
        )
        parser.add_argument(
            '--skip-ensemble',
            action='store_true',
            help='Skip loading Ensemble Control Points data'
        )

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        clear_data = options['clear']
        dry_run = options['dry_run']

        start_time = datetime.now()
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('FLOODWATCH STATIC DATA LOADER'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Start time: {start_time}')
        self.stdout.write(f'Data directory: {data_dir}')
        self.stdout.write(f'Mode: {"DRY RUN" if dry_run else "LIVE"}')
        self.stdout.write(f'Clear existing: {clear_data}')
        self.stdout.write('=' * 70 + '\n')

        total_loaded = 0
        errors = []

        # Load Admin0 (country boundaries) data
        if not options['skip_admin0']:
            try:
                count = self.load_admin0(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'Admin0: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Admin0: {str(e)}'))

        # Load Admin1 data
        if not options['skip_admin1']:
            try:
                count = self.load_admin1(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'Admin1: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Admin1: {str(e)}'))

        # Load Admin2 data
        if not options['skip_admin2']:
            try:
                count = self.load_admin2(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'Admin2: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Admin2: {str(e)}'))

        # Load Lakes data
        if not options['skip_lakes']:
            try:
                count = self.load_lakes(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'Lakes: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Lakes: {str(e)}'))

        # Load HydroRIVERS data
        if not options['skip_rivers']:
            try:
                count = self.load_rivers(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'Rivers: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Rivers: {str(e)}'))

        # Load MonitoringStation data
        if not options['skip_stations']:
            try:
                count = self.load_monitoring_stations(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'MonitoringStations: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load MonitoringStations: {str(e)}'))

        # Load Ensemble Control Points data
        if not options['skip_ensemble']:
            try:
                count = self.load_ensemble_control_points(data_dir, clear_data, dry_run)
                total_loaded += count
            except Exception as e:
                errors.append(f'EnsembleControlPoints: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Ensemble Control Points: {str(e)}'))

        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total records loaded: {total_loaded}')
        self.stdout.write(f'Duration: {duration}')

        if errors:
            self.stdout.write(self.style.ERROR(f'Errors encountered: {len(errors)}'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ All data loaded successfully!'))

        self.stdout.write('=' * 70)

    def load_admin0(self, data_dir, clear_data, dry_run):
        """Load Admin0 (Country) boundaries"""
        self.stdout.write(self.style.NOTICE('\n🌍 LOADING ADMIN0 (Country Boundaries)'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'GHA_EA_admin0.geojson')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'GHA_EA_admin0.geojson not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load Admin0 data'))
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))

        # Clear existing data if requested
        if clear_data:
            count = Admin0.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing Admin0 records...')
                Admin0.objects.all().delete()

        # Load GeoJSON
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        self.stdout.write(f'📥 Loading {len(features)} Admin0 (country) features...')

        loaded_count = 0
        failed_count = 0

        for idx, feature in enumerate(features, 1):
            try:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry')

                if not geometry:
                    self.stdout.write(self.style.WARNING(f'⚠️  Skipping feature {idx}: No geometry'))
                    failed_count += 1
                    continue

                geom = GEOSGeometry(json.dumps(geometry))

                with transaction.atomic():
                    Admin0.objects.create(
                        objectid_1=properties.get('OBJECTID_1'),
                        fid_1=properties.get('fid_1'),
                        gid_0=properties.get('GID_0'),
                        country=properties.get('COUNTRY'),
                        objectid=properties.get('OBJECTID'),
                        shape_leng=properties.get('Shape_Leng', 0),
                        shape_le_1=properties.get('Shape_Le_1', 0),
                        shape_area=properties.get('Shape_Area', 0),
                        geom=geom
                    )
                    loaded_count += 1

                    if loaded_count % 5 == 0:
                        self.stdout.write(f'  Progress: {loaded_count}/{len(features)}')

            except Exception as e:
                failed_count += 1
                if failed_count <= 10:
                    logger.error(f'Failed to load Admin0 feature {idx}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count} Admin0 (country) records'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count

    def load_admin1(self, data_dir, clear_data, dry_run):
        """Load Admin1 (Country) boundaries"""
        self.stdout.write(self.style.NOTICE('\n📍 LOADING ADMIN1 (Countries)'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'GHA_EA_admin1.geojson')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'GHA_EA_admin1.geojson not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load Admin1 data'))
            # Count features in file
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))

        # Clear existing data if requested
        if clear_data:
            count = Admin1.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing Admin1 records...')
                Admin1.objects.all().delete()

        # Load GeoJSON
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        self.stdout.write(f'📥 Loading {len(features)} Admin1 features...')

        loaded_count = 0
        failed_count = 0

        for idx, feature in enumerate(features, 1):
            try:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry')

                if not geometry:
                    self.stdout.write(self.style.WARNING(f'⚠️  Skipping feature {idx}: No geometry'))
                    failed_count += 1
                    continue

                geom = GEOSGeometry(json.dumps(geometry))

                with transaction.atomic():
                    # Admin1 model fields: objectid, country, area, shape_leng, shape_area, land_under, geom
                    Admin1.objects.create(
                        objectid=properties.get('OBJECTID'),
                        country=properties.get('ADM0_NAME', '') or properties.get('COUNTRY', ''),
                        area=properties.get('Shape_Area', 0),
                        shape_leng=properties.get('Shape_Leng', 0),
                        shape_area=properties.get('Shape_Area', 0),
                        land_under=properties.get('REGION', ''),
                        geom=geom
                    )
                    loaded_count += 1

                    if loaded_count % 10 == 0:
                        self.stdout.write(f'  Progress: {loaded_count}/{len(features)}')

            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'❌ Failed to load Admin1 feature {idx}: {str(e)}'))
                logger.error(f'Failed to load Admin1 feature {idx}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count} Admin1 records'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count

    def load_admin2(self, data_dir, clear_data, dry_run):
        """Load Admin2 (Province/District) boundaries"""
        self.stdout.write(self.style.NOTICE('\n📍 LOADING ADMIN2 (Provinces/Districts)'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'GHA_EA_admin2.geojson')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'GHA_EA_admin2.geojson not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load Admin2 data'))
            # Count features in file
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))

        # Clear existing data if requested
        if clear_data:
            count = Admin2.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing Admin2 records...')
                Admin2.objects.all().delete()

        # Load GeoJSON
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        self.stdout.write(f'📥 Loading {len(features)} Admin2 features...')

        loaded_count = 0
        failed_count = 0

        with transaction.atomic():
            for idx, feature in enumerate(features, 1):
                try:
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry')

                    if geometry:
                        geom = GEOSGeometry(json.dumps(geometry))

                        # Admin2 model fields: objectid, country, adm1_name, adm2_name, area, shape_leng, shape_area, land_under, geom
                        Admin2.objects.create(
                            objectid=properties.get('OBJECTID'),
                            country=properties.get('COUNTRY', ''),
                            adm1_name=properties.get('NAME_1', ''),
                            adm2_name=properties.get('NAME_2', '') or properties.get('ENGTYPE_1', ''),
                            area=properties.get('Shape_Area', 0),
                            shape_leng=properties.get('Shape_Leng', 0),
                            shape_area=properties.get('Shape_Area', 0),
                            land_under=properties.get('TYPE_1', ''),
                            geom=geom
                        )
                        loaded_count += 1

                        if loaded_count % 50 == 0:
                            self.stdout.write(f'  Progress: {loaded_count}/{len(features)}')

                except Exception as e:
                    failed_count += 1
                    logger.error(f'Failed to load Admin2 feature {idx}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count} Admin2 records'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count

    def load_lakes(self, data_dir, clear_data, dry_run):
        """Load Lakes and water bodies"""
        self.stdout.write(self.style.NOTICE('\n💧 LOADING LAKES'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'Lakes.geojson')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'Lakes.geojson not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load Lakes data'))
            # Count features in file
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))

        # Clear existing data if requested
        if clear_data:
            count = WaterBodies.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing WaterBodies records...')
                WaterBodies.objects.all().delete()

        # Load GeoJSON
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        self.stdout.write(f'📥 Loading {len(features)} Lakes features...')

        loaded_count = 0
        failed_count = 0

        with transaction.atomic():
            for idx, feature in enumerate(features, 1):
                try:
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry')

                    if geometry:
                        geom = GEOSGeometry(json.dumps(geometry))

                        # WaterBodies model fields: fid, af_wtr_id, sqkm, name_of_wa, type_of_wa, shape_area, shape_len, geom
                        WaterBodies.objects.create(
                            fid=properties.get('AF_WTR_ID', 0),  # Use AF_WTR_ID as fid
                            af_wtr_id=properties.get('AF_WTR_ID', 0),
                            sqkm=properties.get('SQKM', 0),
                            name_of_wa=properties.get('NAME_OF_WA', ''),
                            type_of_wa=properties.get('TYPE_OF_WA', ''),
                            shape_area=properties.get('Shape_area', 0),
                            shape_len=properties.get('Shape_len', 0),
                            geom=geom
                        )
                        loaded_count += 1

                        if loaded_count % 50 == 0:
                            self.stdout.write(f'  Progress: {loaded_count}/{len(features)}')

                except Exception as e:
                    failed_count += 1
                    logger.error(f'Failed to load Lakes feature {idx}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count} Lakes records'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count

    def load_rivers(self, data_dir, clear_data, dry_run):
        """Load HydroRIVERS river network data from GeoJSON"""
        self.stdout.write(self.style.NOTICE('\n🌊 LOADING HYDRO RIVERS'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'HydroRIVERS_v10_GHA.geojson')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'HydroRIVERS_v10_GHA.geojson not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load HydroRIVERS data'))
            # Count features in file
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))

        # Clear existing data if requested
        if clear_data:
            count = HydroRivers.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing HydroRivers records...')
                HydroRivers.objects.all().delete()

        # Load GeoJSON
        self.stdout.write(f'📥 Loading HydroRIVERS data (this may take several minutes)...')
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        self.stdout.write(f'📥 Processing {len(features)} river segments...')

        loaded_count = 0
        failed_count = 0
        batch_size = 5000

        # Process in batches for better performance
        for batch_start in range(0, len(features), batch_size):
            batch_end = min(batch_start + batch_size, len(features))
            batch = features[batch_start:batch_end]

            rivers_to_create = []
            for idx, feature in enumerate(batch, batch_start + 1):
                try:
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry')

                    if geometry:
                        geom = GEOSGeometry(json.dumps(geometry))

                        rivers_to_create.append(HydroRivers(
                            hyriv_id=properties.get('HYRIV_ID'),
                            next_down=properties.get('NEXT_DOWN', 0),
                            main_riv=properties.get('MAIN_RIV', 0),
                            length_km=properties.get('LENGTH_KM', 0.0),
                            dist_dn_km=properties.get('DIST_DN_KM', 0.0),
                            dist_up_km=properties.get('DIST_UP_KM', 0.0),
                            catch_skm=properties.get('CATCH_SKM', 0.0),
                            upland_skm=properties.get('UPLAND_SKM', 0.0),
                            endorheic=properties.get('ENDORHEIC', 0),
                            dis_av_cms=properties.get('DIS_AV_CMS', 0.0),
                            ord_stra=properties.get('ORD_STRA', 0),
                            ord_clas=properties.get('ORD_CLAS', 0),
                            ord_flow=properties.get('ORD_FLOW', 0),
                            hybas_l12=properties.get('HYBAS_L12', 0),
                            geometry=geom
                        ))

                except Exception as e:
                    failed_count += 1
                    if failed_count <= 10:  # Only log first 10 errors
                        logger.error(f'Failed to load river feature {idx}: {str(e)}')

            # Bulk create batch
            if rivers_to_create:
                with transaction.atomic():
                    HydroRivers.objects.bulk_create(rivers_to_create, batch_size=batch_size)
                    loaded_count += len(rivers_to_create)

            # Progress update
            self.stdout.write(f'  Progress: {loaded_count:,}/{len(features):,} ({(loaded_count/len(features)*100):.1f}%)')

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count:,} HydroRIVERS river segments'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count

    def load_monitoring_stations(self, data_dir, clear_data, dry_run):
        """Load MonitoringStation data from shapefile"""
        self.stdout.write(self.style.NOTICE('\n📡 LOADING MONITORING STATIONS'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'fp_sections_igad.shp')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'fp_sections_igad.shp not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load MonitoringStation data'))
            # Count features in shapefile
            ds = DataSource(file_path)
            layer = ds[0]
            return len(layer)

        # Clear existing data if requested
        if clear_data:
            count = MonitoringStation.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing MonitoringStation records...')
                MonitoringStation.objects.all().delete()

        # Load Shapefile
        ds = DataSource(file_path)
        layer = ds[0]
        self.stdout.write(f'📥 Loading {len(layer)} MonitoringStation features...')

        loaded_count = 0
        failed_count = 0

        with transaction.atomic():
            for idx, feature in enumerate(layer, 1):
                try:
                    # MonitoringStation model fields: sec_name, sec_code, basin, station_type,
                    # admin_b_l1, domain, q_thr1, q_thr2, q_thr3, area, geometry, latest_data_date
                    MonitoringStation.objects.create(
                        sec_name=feature.get('SEC_NAME') or feature.get('sec_name') or '',
                        sec_code=feature.get('SEC_CODE') or feature.get('sec_code') or 0,
                        basin=feature.get('BASIN') or feature.get('basin') or '',
                        station_type=feature.get('TYPE') or feature.get('type') or 'unknown',
                        admin_b_l1=feature.get('ADMIN_B_L1') or feature.get('admin_b_l1') or '',
                        domain=feature.get('DOMAIN') or feature.get('domain') or 'IGAD',
                        q_thr1=float(feature.get('Q_THR1') or feature.get('q_thr1') or 0),
                        q_thr2=float(feature.get('Q_THR2') or feature.get('q_thr2') or 0),
                        q_thr3=float(feature.get('Q_THR3') or feature.get('q_thr3') or 0),
                        area=float(feature.get('AREA') or feature.get('area') or 0),
                        geometry=GEOSGeometry(feature.geom.wkt),
                        latest_data_date=date.today()
                    )
                    loaded_count += 1

                    if loaded_count % 50 == 0:
                        self.stdout.write(f'  Progress: {loaded_count}/{len(layer)}')

                except Exception as e:
                    failed_count += 1
                    logger.error(f'Failed to load MonitoringStation feature {idx}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count} MonitoringStation records'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count

    def load_ensemble_control_points(self, data_dir, clear_data, dry_run):
        """Load Ensemble Control Points from GeoJSON file"""
        self.stdout.write(self.style.NOTICE('\n🎯 LOADING ENSEMBLE CONTROL POINTS'))
        self.stdout.write('-' * 40)

        file_path = os.path.join(data_dir, 'ensemble_control_file.geojson')

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'ensemble_control_file.geojson not found at {file_path}')

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.stdout.write(f'📁 File: {file_path}')
        self.stdout.write(f'📊 Size: {file_size:.2f} MB')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN: Would load Ensemble Control Points data'))
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))

        # Clear existing data if requested
        if clear_data:
            count = EnsembleControlPoint.objects.count()
            if count > 0:
                self.stdout.write(f'🗑️  Clearing {count} existing Ensemble Control Points...')
                EnsembleControlPoint.objects.all().delete()

        # Load GeoJSON
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        self.stdout.write(f'📥 Loading {len(features)} Ensemble Control Points (for forecast merging)...')

        loaded_count = 0
        failed_count = 0
        batch_size = 500
        control_points = []

        for idx, feature in enumerate(features, 1):
            try:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates', [])

                if len(coordinates) != 2:
                    failed_count += 1
                    continue

                # Create Point geometry
                lon, lat = coordinates
                point = Point(lon, lat, srid=4326)

                # Extract properties
                point_id = properties.get('ID')
                gridcode = properties.get('GRIDCODE')
                admin_name = properties.get('admin_name')
                x = properties.get('x')
                y = properties.get('y')
                zone = properties.get('Zone')
                is_node = properties.get('Node', True)

                # Validate required fields
                if point_id is None or gridcode is None or x is None or y is None or zone is None:
                    failed_count += 1
                    continue

                # Create model instance
                control_points.append(EnsembleControlPoint(
                    point_id=point_id,
                    gridcode=gridcode,
                    admin_name=admin_name,
                    x=x,
                    y=y,
                    zone=zone,
                    is_node=is_node,
                    geom=point
                ))

                # Batch insert
                if len(control_points) >= batch_size:
                    with transaction.atomic():
                        EnsembleControlPoint.objects.bulk_create(
                            control_points,
                            ignore_conflicts=True
                        )
                    loaded_count += len(control_points)
                    self.stdout.write(f'  Progress: {loaded_count}/{len(features)}')
                    control_points = []

            except Exception as e:
                failed_count += 1
                if failed_count <= 10:  # Only log first 10 errors
                    logger.error(f'Failed to load Ensemble Control Point {idx}: {str(e)}')

        # Insert remaining control points
        if control_points:
            with transaction.atomic():
                EnsembleControlPoint.objects.bulk_create(
                    control_points,
                    ignore_conflicts=True
                )
            loaded_count += len(control_points)

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {loaded_count} Ensemble Control Points'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Failed to load {failed_count} records'))

        return loaded_count