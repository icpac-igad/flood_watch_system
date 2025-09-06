#!/usr/bin/env python3
"""
Extend the existing ibew_getfeatureinfo.map file with remaining dates for the year
This script reads the current file, finds the last date, and adds layers for the rest of the year
"""

import re
from datetime import datetime, timedelta

# Layer types to generate (based on existing patterns)
LAYER_TYPES = [
    ("healthtot", "Health Centers Affected"),
    ("popaff100", "People Affected 100cm"),
    ("popaff25", "People Affected 25cm"), 
    ("popafftot", "Total People Affected"),
    ("popage100", "Vulnerable Age Groups 100cm"),
    ("popage25", "Vulnerable Age Groups 25cm"),
    ("popmob100", "Reduced Mobility 100cm"),
    ("popmob25", "Reduced Mobility 25cm")
]

def find_existing_dates(file_content):
    """Find all existing dates in the mapfile"""
    # Pattern to match layer names like "healthtot_20250624"
    pattern = r'NAME "(\w+)_(\d{8})"'
    matches = re.findall(pattern, file_content)
    
    dates = set()
    for layer_type, date_str in matches:
        dates.add(date_str)
    
    return sorted(dates)

def get_latest_date(dates):
    """Get the latest date from the list"""
    if not dates:
        return None
    return max(dates)

def generate_layer(layer_name, layer_title, date_str, formatted_date):
    """Generate a single layer definition matching the existing format"""
    return f"""
  # {layer_title} - {formatted_date}
  LAYER
    NAME "{layer_name}_{date_str}"
    STATUS ON
    TYPE POLYGON
    DATA "shapefiles/ibew_shapefiles/{date_str}0000_FPimpacts-{layer_name}"
    TEMPLATE "query"
    PROJECTION
      "init=epsg:4326"
    END
    METADATA
      "wms_title" "{layer_title} - {formatted_date}"
      "wms_enable_request" "*"
      "gml_include_items" "all"
      "wms_include_items" "all"
    END
    CLASSITEM "flood_tot"
    CLASS
      NAME "No Impact"
      EXPRESSION ([flood_tot] = 0)
      STYLE
        COLOR 240 240 240
        OUTLINECOLOR 200 200 200
        WIDTH 0.5
      END
    END
    CLASS
      NAME "Impact"
      EXPRESSION ([flood_tot] > 0)
      STYLE
        COLOR 255 0 0
        OUTLINECOLOR 150 150 150
        WIDTH 0.5
        OPACITY 70
      END
    END
  END"""

def main():
    # Read the existing mapfile
    try:
        with open("ibew_getfeatureinfo.map", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: ibew_getfeatureinfo.map file not found!")
        return
    
    # Find existing dates
    existing_dates = find_existing_dates(content)
    print(f"Found {len(existing_dates)} existing dates in the mapfile")
    
    if existing_dates:
        latest_date_str = get_latest_date(existing_dates)
        latest_date = datetime.strptime(latest_date_str, "%Y%m%d")
        print(f"Latest date found: {latest_date.strftime('%Y-%m-%d')}")
    else:
        # If no dates found, start from a default date
        latest_date = datetime(2025, 6, 24)  # Based on your example
        print(f"No existing dates found, starting from: {latest_date.strftime('%Y-%m-%d')}")
    
    # Generate layers for remaining dates until end of year
    end_date = datetime(2025, 12, 31)
    current_date = latest_date + timedelta(days=1)
    
    new_layers = []
    days_added = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        formatted_date = current_date.strftime("%Y-%m-%d")
        
        # Skip if this date already exists
        if date_str in existing_dates:
            current_date += timedelta(days=1)
            continue
        
        # Generate layers for all types for this date
        for layer_name, layer_title in LAYER_TYPES:
            new_layers.append(generate_layer(layer_name, layer_title, date_str, formatted_date))
        
        current_date += timedelta(days=1)
        days_added += 1
    
    if new_layers:
        # Find the position to insert new layers (before the final END)
        # Remove the last "END" and add new layers
        if content.strip().endswith("END"):
            content = content.strip()[:-3]  # Remove last "END"
        
        # Add new layers
        extended_content = content + "\n".join(new_layers) + "\nEND"
        
        # Write the extended file
        with open("ibew_getfeatureinfo_extended.map", "w") as f:
            f.write(extended_content)
        
        print(f"Added {days_added} new days")
        print(f"Added {len(new_layers)} new layers")
        print("Extended mapfile saved as: ibew_getfeatureinfo_extended.map")
        print("\nTo use the extended file:")
        print("1. Copy ibew_getfeatureinfo_extended.map to your staging server")
        print("2. Replace the original ibew_getfeatureinfo.map with the extended version")
    else:
        print("No new dates to add - the mapfile already covers the full year")

if __name__ == "__main__":
    main()