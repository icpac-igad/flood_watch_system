#!/bin/bash

set -e

# set nginx configs from env var
CONF_FILE=${NGINX_CONF_FILE:-/etc/nginx/nginx.conf}

# path variables on nginx.conf
sed -i "s|\[LOGS_DIR\]|${LOGS_DIR:-/var/log/nginx}|g" ${CONF_FILE}
sed -i "s|\[KEEPALIVE_CONNS\]|${KEEPALIVE_CONNS:-12}|g" ${CONF_FILE}

# set env vars on config file
sed -i "s|\[MS_DEBUGLEVEL\]|${MS_DEBUGLEVEL:-2}|g" ${MAPFILES_DIR}/mapserver.conf
sed -i "s|\[MS_ERRORFILE\]|${MS_ERRORFILE:-stderr}|g" ${MAPFILES_DIR}/mapserver.conf
sed -i "s|\[MS_MAPFILE\]|${MS_MAPFILE}|g" ${MAPFILES_DIR}/mapserver.conf

# Set webserver variables in web metadata mapfiles
sed -i "s|\[MS_SERVICE_URL\]|${MS_SERVICE_URL}|g" ${MAPFILES_DIR}/config/wms-metadata.map

# Set DB parameters in database.map
sed -i 's/\[DB_HOST\]/'${DB_HOST}'/' ${MAPFILES_DIR}/config/database.map
sed -i 's/\[DB_USER\]/'${DB_MAP_USER}'/' ${MAPFILES_DIR}/config/database.map
sed -i 's/\[DB_PWD\]/'${DB_MAP_USER_PASSWORD}'/' ${MAPFILES_DIR}/config/database.map
sed -i 's/\[DB_NAME\]/'${DB_NAME}'/' ${MAPFILES_DIR}/config/database.map
sed -i 's/\[DB_PORT\]/'${DB_PORT}'/' ${MAPFILES_DIR}/config/database.map

# set correct directory paths on main mapfile
sed -i "s|\[MS_DEBUGLEVEL\]|${MS_DEBUGLEVEL:-2}|g" ${MAPFILES_DIR}/mapserver.map
sed -i "s|\[MS_MAP_EXTENT\]|${WGS84_GRID_EXTENTS}|g" ${MAPFILES_DIR}/mapserver.map

# Start spawn-fcgi in the background
spawn-fcgi -a 127.0.0.1 -p 9001 -F ${MAX_PROCESSES:-10} -u ${USER_NAME:-starship} -U ${USER_NAME:-starship} -P /tmp/mapserv_fcgi.pid -- /usr/local/bin/mapserv_wrapper &

# Start Nginx in the foreground
nginx -g "daemon off;"