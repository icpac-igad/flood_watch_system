"""
Management command to load merged ensemble forecast GeoJSON into database.

This command:
1. Reads the merged ensemble_with_forecasts.geojson file
2. Extracts the latest forecast date from the embedded data
3. Saves to EnsembleForecastGeoJSON model

Usage:
    python manage.py load_ensemble_forecast
    python manage.py load_ensemble_forecast --force  # Re-load even if exists
"""

from django.core.management.base import BaseCommand
from Impact.models import EnsembleForecastGeoJSON
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load merged ensemble forecast GeoJSON into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload even if data already exists in database',
        )
        parser.add_argument(
            '--file',
            type=str,
            default='static_data/ensemble_with_forecasts.geojson',
            help='Path to the merged ensemble GeoJSON file',
        )

    def extract_latest_date_from_geojson(self, geojson_data):
        """Extract the latest forecast date from the GeoJSON features.

        Looks through all features' forecast data to find the most recent date.
        """
        latest_date = None

        for feature in geojson_data.get('features', []):
            forecasts = feature.get('properties', {}).get('forecasts', [])

            for forecast in forecasts:
                date_str = forecast.get('date')
                if date_str:
                    try:
                        # Parse date string (format: YYYY-MM-DD)
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                        if latest_date is None or date_obj > latest_date:
                            latest_date = date_obj
                    except ValueError:
                        continue

        return latest_date

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting ensemble forecast GeoJSON load...'))

        # Get file path
        geojson_file = Path(options['file'])

        if not geojson_file.exists():
            self.stdout.write(self.style.ERROR(f'GeoJSON file not found: {geojson_file}'))
            self.stdout.write(self.style.WARNING('Run "python scripts/merge_ensemble_forecast.py" first to generate it'))
            return

        # Load the GeoJSON file
        self.stdout.write(f'Loading GeoJSON from: {geojson_file}')

        try:
            with open(geojson_file, 'r') as f:
                geojson_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load GeoJSON file: {e}'))
            logger.exception('Failed to load GeoJSON file')
            return

        # Extract metadata
        metadata = geojson_data.get('metadata', {})
        total_features = metadata.get('total_features', len(geojson_data.get('features', [])))
        features_with_data = metadata.get('features_with_data', 0)
        features_without_data = metadata.get('features_without_data', 0)

        self.stdout.write(f'  Total features: {total_features}')
        self.stdout.write(f'  Features with data: {features_with_data}')
        self.stdout.write(f'  Features without data: {features_without_data}')

        # Extract the latest forecast date from the data
        latest_date = self.extract_latest_date_from_geojson(geojson_data)

        if not latest_date:
            self.stdout.write(self.style.ERROR('Could not extract forecast date from GeoJSON data'))
            return

        date_string = latest_date.strftime('%Y%m%d')

        self.stdout.write(f'  Latest forecast date: {latest_date} ({date_string})')

        # Check if already exists
        if not options['force']:
            if EnsembleForecastGeoJSON.objects.filter(data_date=latest_date).exists():
                self.stdout.write(self.style.WARNING(
                    f'Data for {latest_date} already exists in database. Use --force to reload.'
                ))
                return

        # Save to database
        try:
            obj, created = EnsembleForecastGeoJSON.objects.update_or_create(
                data_date=latest_date,
                defaults={
                    'date_string': date_string,
                    'geojson_data': geojson_data,
                    'feature_count': total_features,
                    'features_with_data': features_with_data,
                    'features_without_data': features_without_data,
                    'file_path': str(geojson_file),
                    'processed_by': 'load_ensemble_forecast',
                }
            )

            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ {action} ensemble forecast record for {latest_date}'
            ))
            self.stdout.write(f'  Features: {features_with_data}/{total_features} with data')
            self.stdout.write(f'  Database ID: {obj.id}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to save to database: {e}'))
            logger.exception('Failed to save ensemble forecast to database')
            return

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Ensemble forecast load complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))
