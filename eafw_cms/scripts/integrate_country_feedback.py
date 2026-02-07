#!/usr/bin/env python3
"""
Country Feedback Integration Script

This script integrates member state feedback on forecast locations into the
multimodal forecast system. It preserves all existing data while adding
a 'country_selected' flag to mark points that countries have approved.

Data Sources:
- Ethiopia: Ethiopia.xlsx, Selected_River Gauging Stations.xlsx
- Rwanda: Rwanda-forecast-lacations.xlsx, Selected_River Gauging Stations.xlsx
- Sudan: Sudan_ modified.xlsx
- South Sudan: Calibration_Locations.csv
- Uganda: (to be added when extracted)

Usage:
    python scripts/integrate_country_feedback.py --feedback-dir /path/to/country_feedback
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import math

# Add Django settings
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geomanagerweb.settings.base')

import django
django.setup()

import pandas as pd
from django.db import transaction

from home.models import MultimodalForecastPoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Country code mapping
COUNTRY_CODES = {
    'ET': 'Ethiopia',
    'RW': 'Rwanda',
    'SD': 'Sudan',
    'SS': 'South Sudan',
    'UG': 'Uganda',
    'KE': 'Kenya',
    'TZ': 'Tanzania',
    'DJ': 'Djibouti',
    'ER': 'Eritrea',
    'SO': 'Somalia',
}

# Coordinate matching tolerance (in degrees, ~1km)
COORD_TOLERANCE = 0.01


def parse_dms_to_decimal(dms_str: str) -> Optional[float]:
    """Convert DMS (degrees, minutes, seconds) string to decimal degrees."""
    if pd.isna(dms_str) or not dms_str:
        return None

    try:
        # Handle formats like "8°23'00''" or "38°47' 0''"
        dms_str = str(dms_str).strip()

        # Extract degrees, minutes, seconds
        parts = dms_str.replace('°', ' ').replace("'", ' ').replace('"', ' ').split()

        degrees = float(parts[0]) if len(parts) > 0 else 0
        minutes = float(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[2]) if len(parts) > 2 else 0

        decimal = degrees + minutes / 60 + seconds / 3600

        # Check for negative (South/West)
        if 'S' in dms_str or 'W' in dms_str or degrees < 0:
            decimal = -abs(decimal)

        return decimal
    except (ValueError, IndexError) as e:
        logger.warning(f"Could not parse DMS: {dms_str} - {e}")
        return None


def load_ethiopia_data(feedback_dir: Path) -> pd.DataFrame:
    """Load Ethiopia feedback data."""
    ethiopia_dir = feedback_dir / "Ethiopia"
    all_points = []

    # Main grid points file
    main_file = ethiopia_dir / "Ethiopia.xlsx"
    if main_file.exists():
        df = pd.read_excel(main_file)
        # Filter to selected points only
        selected = df[df['Selected (Yes/No)'].str.lower().str.strip() == 'yes'].copy()
        selected['country_code'] = 'ET'
        selected['source'] = 'grid_selection'
        selected['lon'] = selected['x']
        selected['lat'] = selected['y']
        all_points.append(selected[['country_code', 'lon', 'lat', 'Admin1', 'Admin2', 'GRID_CODE', 'source']])
        logger.info(f"Ethiopia: {len(selected)} selected grid points from {len(df)} total")

    # River gauging stations
    stations_file = ethiopia_dir / "Selected_River Gauging Stations.xlsx"
    if stations_file.exists():
        df = pd.read_excel(stations_file, header=None)
        # Parse the station data (non-standard format)
        stations = []
        for idx, row in df.iterrows():
            if idx == 0:  # Skip header
                continue
            try:
                name = row[1] if pd.notna(row[1]) else None
                lat_str = row[2] if pd.notna(row[2]) else None
                lon_str = row[3] if pd.notna(row[3]) else None

                if name and lat_str and lon_str:
                    lat = parse_dms_to_decimal(str(lat_str))
                    lon = parse_dms_to_decimal(str(lon_str))
                    if lat and lon:
                        stations.append({
                            'country_code': 'ET',
                            'lon': lon,
                            'lat': lat,
                            'Admin1': name,
                            'Admin2': '',
                            'GRID_CODE': None,
                            'source': 'gauging_station'
                        })
            except Exception as e:
                logger.warning(f"Error parsing Ethiopia station row {idx}: {e}")

        if stations:
            all_points.append(pd.DataFrame(stations))
            logger.info(f"Ethiopia: {len(stations)} gauging stations")

    return pd.concat(all_points, ignore_index=True) if all_points else pd.DataFrame()


def load_rwanda_data(feedback_dir: Path) -> pd.DataFrame:
    """Load Rwanda feedback data."""
    rwanda_dir = feedback_dir / "Rwanda"
    all_points = []

    # Main grid points file
    main_file = rwanda_dir / "Rwanda-forecast-lacations.xlsx"
    if main_file.exists():
        df = pd.read_excel(main_file)
        selected = df[df['Selected (Yes/No)'].str.upper().str.strip() == 'YES'].copy()
        selected['country_code'] = 'RW'
        selected['source'] = 'grid_selection'
        selected['lon'] = selected['x']
        selected['lat'] = selected['y']
        all_points.append(selected[['country_code', 'lon', 'lat', 'Admin1', 'Admin2', 'GRID_CODE', 'source']])
        logger.info(f"Rwanda: {len(selected)} selected grid points from {len(df)} total")

    # River gauging stations
    stations_file = rwanda_dir / "Selected_River Gauging Stations.xlsx"
    if stations_file.exists():
        df = pd.read_excel(stations_file, header=None)
        stations = []
        for idx, row in df.iterrows():
            if idx == 0:  # Skip header
                continue
            try:
                name = row[1] if pd.notna(row[1]) else None
                lon = row[3] if pd.notna(row[3]) else None
                lat = row[4] if pd.notna(row[4]) else None

                if name and lon and lat:
                    stations.append({
                        'country_code': 'RW',
                        'lon': float(lon),
                        'lat': float(lat),
                        'Admin1': name,
                        'Admin2': row[2] if pd.notna(row[2]) else '',
                        'GRID_CODE': None,
                        'source': 'gauging_station'
                    })
            except Exception as e:
                logger.warning(f"Error parsing Rwanda station row {idx}: {e}")

        if stations:
            all_points.append(pd.DataFrame(stations))
            logger.info(f"Rwanda: {len(stations)} gauging stations")

    return pd.concat(all_points, ignore_index=True) if all_points else pd.DataFrame()


def load_sudan_data(feedback_dir: Path) -> pd.DataFrame:
    """Load Sudan feedback data."""
    sudan_dir = feedback_dir / "Sudan"

    # Modified file with selections
    main_file = sudan_dir / "Sudan_ modified.xlsx"
    if main_file.exists():
        df = pd.read_excel(main_file)
        # Check if any selections marked
        if 'Selected (Yes/No)' in df.columns:
            has_selection = df['Selected (Yes/No)'].notna()
            selected = df[df['Selected (Yes/No)'].str.lower().str.strip() == 'yes'].copy() if has_selection.any() else df.copy()
        else:
            selected = df.copy()

        selected['country_code'] = 'SD'
        selected['source'] = 'grid_selection'
        selected['lon'] = selected['x']
        selected['lat'] = selected['y']

        # If no selections marked, include all (pending country review)
        if 'Selected (Yes/No)' not in df.columns or not has_selection.any():
            selected['pending_review'] = True
            logger.info(f"Sudan: {len(selected)} points (pending country selection)")
        else:
            logger.info(f"Sudan: {len(selected)} selected grid points")

        return selected[['country_code', 'lon', 'lat', 'Admin1', 'Admin2', 'GRID_CODE', 'source']]

    return pd.DataFrame()


def load_south_sudan_data(feedback_dir: Path) -> pd.DataFrame:
    """Load South Sudan feedback data."""
    ss_dir = feedback_dir / "South Sudan"

    # Calibration locations CSV
    csv_file = ss_dir / "Calibration_Locations.csv"
    if csv_file.exists():
        df = pd.read_csv(csv_file)
        df['country_code'] = 'SS'
        df['source'] = 'calibration_station'
        df['lon'] = df['Longitude (WGS-84)']
        df['lat'] = df['Latitude  (WGS-84)']
        df['Admin1'] = df['Station_Name']
        df['Admin2'] = ''
        df['GRID_CODE'] = None

        logger.info(f"South Sudan: {len(df)} calibration stations")
        return df[['country_code', 'lon', 'lat', 'Admin1', 'Admin2', 'GRID_CODE', 'source']]

    return pd.DataFrame()


def load_all_feedback(feedback_dir: Path) -> pd.DataFrame:
    """Load all country feedback data into a single DataFrame."""
    feedback_dir = Path(feedback_dir)

    all_data = []

    # Load each country
    ethiopia = load_ethiopia_data(feedback_dir)
    if not ethiopia.empty:
        all_data.append(ethiopia)

    rwanda = load_rwanda_data(feedback_dir)
    if not rwanda.empty:
        all_data.append(rwanda)

    sudan = load_sudan_data(feedback_dir)
    if not sudan.empty:
        all_data.append(sudan)

    south_sudan = load_south_sudan_data(feedback_dir)
    if not south_sudan.empty:
        all_data.append(south_sudan)

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"Total feedback points: {len(combined)}")
        return combined

    return pd.DataFrame()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance between two points in km."""
    R = 6371  # Earth's radius in km

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def match_feedback_to_existing(feedback_df: pd.DataFrame, existing_points: List[Dict]) -> Dict[int, Dict]:
    """
    Match feedback points to existing multimodal points.
    Returns a dict of point_id -> feedback_info for matched points.
    """
    matches = {}
    unmatched_feedback = []

    for _, fb_row in feedback_df.iterrows():
        fb_lon = fb_row['lon']
        fb_lat = fb_row['lat']
        country = fb_row['country_code']

        best_match = None
        best_distance = float('inf')

        for point in existing_points:
            # Check country prefix matches
            if not point['admin_name'].startswith(country):
                continue

            p_lon = point['lon']
            p_lat = point['lat']

            # Calculate distance
            dist = haversine_distance(fb_lat, fb_lon, p_lat, p_lon)

            if dist < best_distance and dist < 5:  # Within 5km
                best_distance = dist
                best_match = point

        if best_match:
            matches[best_match['point_id']] = {
                'country_code': country,
                'source': fb_row['source'],
                'distance_km': best_distance,
                'feedback_admin1': fb_row.get('Admin1', ''),
                'feedback_admin2': fb_row.get('Admin2', ''),
            }
        else:
            unmatched_feedback.append({
                'country': country,
                'lon': fb_lon,
                'lat': fb_lat,
                'admin1': fb_row.get('Admin1', ''),
                'source': fb_row['source']
            })

    logger.info(f"Matched {len(matches)} feedback points to existing points")
    logger.info(f"Unmatched feedback points: {len(unmatched_feedback)}")

    return matches, unmatched_feedback


def update_database(matches: Dict[int, Dict], dry_run: bool = True) -> Dict:
    """
    Update the database to mark matched points as country_selected.
    """
    stats = {
        'updated': 0,
        'errors': 0,
        'already_selected': 0
    }

    if dry_run:
        logger.info("DRY RUN - No database changes will be made")

    try:
        with transaction.atomic():
            for point_id, match_info in matches.items():
                try:
                    point = MultimodalForecastPoint.objects.get(point_id=point_id)

                    # Check if already marked
                    if getattr(point, 'country_selected', False):
                        stats['already_selected'] += 1
                        continue

                    if not dry_run:
                        point.country_selected = True
                        point.selection_source = match_info['source']
                        point.save(update_fields=['country_selected', 'selection_source'])

                    stats['updated'] += 1

                except MultimodalForecastPoint.DoesNotExist:
                    logger.warning(f"Point {point_id} not found in database")
                    stats['errors'] += 1
                except Exception as e:
                    logger.error(f"Error updating point {point_id}: {e}")
                    stats['errors'] += 1

            if dry_run:
                # Rollback in dry run
                raise Exception("Dry run - rolling back")

    except Exception as e:
        if "Dry run" not in str(e):
            logger.error(f"Transaction error: {e}")

    return stats


def generate_report(matches: Dict, unmatched: List, stats: Dict, output_dir: Path):
    """Generate a detailed report of the integration."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'matched_points': len(matches),
            'unmatched_feedback_points': len(unmatched),
            'database_updated': stats.get('updated', 0),
            'errors': stats.get('errors', 0),
        },
        'matches_by_country': {},
        'unmatched_points': unmatched[:50],  # First 50
    }

    # Count by country
    for match_info in matches.values():
        country = match_info['country_code']
        report['matches_by_country'][country] = report['matches_by_country'].get(country, 0) + 1

    # Save report
    report_file = output_dir / f"feedback_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Report saved to: {report_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("INTEGRATION SUMMARY")
    print("=" * 60)
    print(f"Total matched points: {len(matches)}")
    print(f"Unmatched feedback points: {len(unmatched)}")
    print("\nMatches by country:")
    for country, count in sorted(report['matches_by_country'].items()):
        print(f"  {COUNTRY_CODES.get(country, country)}: {count}")
    print("=" * 60)

    return report


def main():
    parser = argparse.ArgumentParser(description='Integrate country feedback into multimodal forecast system')
    parser.add_argument('--feedback-dir', type=str, default='/home/koros/Downloads/country_feedback',
                        help='Directory containing country feedback files')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Run without making database changes')
    parser.add_argument('--apply', action='store_true',
                        help='Actually apply changes to database')
    parser.add_argument('--output-dir', type=str, default='.',
                        help='Directory for output reports')

    args = parser.parse_args()

    dry_run = not args.apply
    feedback_dir = Path(args.feedback_dir)
    output_dir = Path(args.output_dir)

    if not feedback_dir.exists():
        logger.error(f"Feedback directory not found: {feedback_dir}")
        sys.exit(1)

    logger.info(f"Loading feedback from: {feedback_dir}")
    logger.info(f"Dry run: {dry_run}")

    # Load feedback data
    feedback_df = load_all_feedback(feedback_dir)

    if feedback_df.empty:
        logger.error("No feedback data loaded")
        sys.exit(1)

    # Get existing points from database
    logger.info("Loading existing multimodal points from database...")
    existing_points = list(
        MultimodalForecastPoint.objects.values('point_id', 'admin_name', 'geom')
    )

    # Convert geom to lon/lat
    for point in existing_points:
        if point['geom']:
            point['lon'] = point['geom'].x
            point['lat'] = point['geom'].y
        else:
            point['lon'] = None
            point['lat'] = None

    existing_points = [p for p in existing_points if p['lon'] is not None]
    logger.info(f"Loaded {len(existing_points)} existing points")

    # Match feedback to existing points
    matches, unmatched = match_feedback_to_existing(feedback_df, existing_points)

    # Update database
    stats = update_database(matches, dry_run=dry_run)

    # Generate report
    generate_report(matches, unmatched, stats, output_dir)

    if dry_run:
        print("\nThis was a DRY RUN. To apply changes, run with --apply flag")


if __name__ == '__main__':
    main()
