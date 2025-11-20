"""
Management command to update SavedReport records with country and basin data from forecast.
"""
from django.core.management.base import BaseCommand
from Impact.models import SavedReport, MergedDeterministicGeoJSON


class Command(BaseCommand):
    help = 'Update SavedReport records with country and basin data from latest forecast'

    def handle(self, *args, **options):
        # Get latest forecast data
        latest_forecast = MergedDeterministicGeoJSON.objects.order_by('-data_date').first()

        if not latest_forecast:
            self.stdout.write(self.style.ERROR('No forecast data found'))
            return

        self.stdout.write(f'Using forecast data from {latest_forecast.data_date}')
        geojson_data = latest_forecast.geojson_data

        # Get all SavedReports that need updating
        reports = SavedReport.objects.all()
        updated_count = 0
        not_found_count = 0

        for report in reports:
            if not report.station_id:
                continue

            # Find station in forecast data
            station_found = False
            for feature in geojson_data.get('features', []):
                props = feature.get('properties', {})
                station_ids = [
                    str(props.get('ID', '')),
                    str(props.get('SEC_CODE', '')),
                    str(props.get('station_id', '')),
                    str(props.get('section_id', ''))
                ]

                if str(report.station_id) in station_ids:
                    # Extract country from ADMIN_B_L1
                    admin = props.get('ADMIN_B_L1', '')
                    country = ''
                    if admin and ' - ' in admin:
                        country = admin.split(' - ')[0]

                    basin = props.get('BASIN', '')
                    station_name = props.get('SEC_NAME', '')

                    # Update report
                    report.country = country
                    report.basin = basin
                    if station_name and not report.report_title.startswith('Flood Analysis Report'):
                        report.report_title = station_name
                    report.save()

                    updated_count += 1
                    station_found = True
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated Report {report.id}: Station {report.station_id} -> '
                            f'Country="{country}", Basin="{basin}"'
                        )
                    )
                    break

            if not station_found:
                not_found_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Station {report.station_id} not found in forecast data'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nUpdated {updated_count} reports, {not_found_count} stations not found'
            )
        )
