FROM debian:bullseye-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    apache2 \
    cgi-mapserver \
    libapache2-mod-fcgid \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Enable CGI and headers modules
RUN a2enmod cgi headers

# Configure CGI directory
RUN mkdir -p /usr/lib/cgi-bin/ \
    && ln -sf /usr/bin/mapserv /usr/lib/cgi-bin/mapserv \
    && chmod 755 /usr/lib/cgi-bin/mapserv

# Create Apache config
RUN echo '<VirtualHost *:80>\n\
    ServerAdmin webmaster@localhost\n\
    DocumentRoot /var/www/html\n\
    ErrorLog ${APACHE_LOG_DIR}/error.log\n\
    CustomLog ${APACHE_LOG_DIR}/access.log combined\n\
    ScriptAlias /cgi-bin/ /usr/lib/cgi-bin/\n\
    <Directory "/usr/lib/cgi-bin">\n\
        AllowOverride None\n\
        Options +ExecCGI -MultiViews\n\
        Require all granted\n\
    </Directory>\n\
    <Location "/cgi-bin/mapserv">\n\
        SetEnv MS_MAPFILE /etc/mapserver/master.map\n\
        Header set Access-Control-Allow-Origin "*"\n\
    </Location>\n\
</VirtualHost>' > /etc/apache2/sites-available/000-default.conf

# Create health check
RUN echo '#!/bin/bash\n\
echo "Content-Type: text/plain"\n\
echo ""\n\
echo "OK"' > /usr/lib/cgi-bin/health \
    && chmod +x /usr/lib/cgi-bin/health

# Create directories
RUN mkdir -p /etc/mapserver /data/geojson

WORKDIR /etc/mapserver
EXPOSE 80

CMD ["apache2ctl", "-D", "FOREGROUND"]