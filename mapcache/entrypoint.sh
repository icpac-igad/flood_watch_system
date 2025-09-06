#!/bin/bash
set -e

# Check if configuration files exist
if [ ! -f "/etc/mapcache/mapcache.xml" ]; then
    echo "ERROR: MapCache configuration file not found at /etc/mapcache/mapcache.xml"
    exit 1
fi

if [ ! -f "/etc/apache2/sites-available/mapcache.conf" ]; then
    echo "ERROR: Apache configuration file not found at /etc/apache2/sites-available/mapcache.conf"
    exit 1
fi

# Create cache and lock directories if they don't exist
mkdir -p /var/cache/mapcache /var/lock/mapcache

# Fix permissions - make directories writable by www-data
chmod -R 777 /var/cache/mapcache /var/lock/mapcache

# Check Apache configuration
echo "Checking Apache configuration..."
apache2ctl configtest

# Check if MapCache module exists
if [ ! -f "/usr/lib/apache2/modules/mod_mapcache.so" ]; then
    echo "ERROR: MapCache module not found at /usr/lib/apache2/modules/mod_mapcache.so"
    echo "Available modules:"
    ls -la /usr/lib/apache2/modules/ | grep mapcache || echo "No mapcache modules found"
    exit 1
fi

# Enable modules and site if not already enabled
a2enmod rewrite headers 2>/dev/null || true
a2ensite mapcache 2>/dev/null || true

# Verify Apache can load the configuration
echo "Testing MapCache configuration..."
apache2ctl -t -D DUMP_MODULES | grep mapcache || echo "MapCache module not loaded"

echo "Starting MapCache with Apache..."

# Execute the main command
exec "$@"