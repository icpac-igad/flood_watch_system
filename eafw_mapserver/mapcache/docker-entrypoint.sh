#!/bin/bash

set -e

# set nginx configs from env var
CONF_FILE=${NGINX_CONF_FILE:-/etc/nginx/conf/nginx.conf}

# path variables on nginx.conf
sed -i "s|\[LOGS_DIR\]|${LOGS_DIR:-/etc/nginx/logs}|g" ${CONF_FILE}
sed -i "s|\[KEEPALIVE_CONNS\]|${KEEPALIVE_CONNS:-12}|g" ${CONF_FILE}

# generate mapcache.xml config file
echo "generating mapcache config file"
python3 generate_mapcache_config.py mapcache_config.json

# Start spawn-fcgi in the background
# -a: address, -p: port (internal to container)
# -F: number of children/processes to fork
# -P: PID file
# --: separates spawn-fcgi args from the executable args
spawn-fcgi -a 127.0.0.1 -p 9001 -F ${MAX_PROCESSES:-10} -u ${USER_NAME:-starship} -U ${USER_NAME:-starship} -- /usr/local/bin/mapcache.fcgi

# Start Nginx in the foreground
# The -g "daemon off;" part is critical for Docker, as it keeps Nginx
# running in the foreground, allowing the container to stay alive.
nginx -g "daemon off;"

