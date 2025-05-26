FROM debian:bullseye-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    apache2 \
    apache2-dev \
    build-essential \
    cmake \
    curl \
    libcurl4-openssl-dev \
    libfcgi-dev \
    libgdal-dev \
    libgeos-dev \
    libmapserver-dev \
    libpixman-1-dev \
    libpng-dev \
    libpq-dev \
    libproj-dev \
    libsqlite3-dev \
    libxml2-dev \
    pkg-config \
    software-properties-common \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install MapCache from source
WORKDIR /tmp
RUN wget https://github.com/MapServer/mapcache/archive/refs/tags/rel-1-12-1.tar.gz && \
    tar -xf rel-1-12-1.tar.gz && \
    cd mapcache-rel-1-12-1 && \
    mkdir build && \
    cd build && \
    cmake .. -DWITH_SQLITE=ON -DWITH_BERKELEY_DB=OFF -DWITH_MEMCACHE=OFF \
             -DWITH_TIFF=ON -DWITH_GEOTIFF=ON -DWITH_FCGI=ON -DWITH_PCRE=ON && \
    make && \
    make install

# Configure Apache for MapCache
RUN a2enmod rewrite headers

# Create cache and lock directories
RUN mkdir -p /var/cache/mapcache /var/lock/mapcache && \
    chown -R www-data:www-data /var/cache/mapcache /var/lock/mapcache

# Copy Apache configuration
COPY config/apache-mapcache.conf /etc/apache2/sites-available/mapcache.conf
COPY config/mapcache.xml /etc/mapcache/mapcache.xml

# Enable the site
RUN a2ensite mapcache

# Expose port
EXPOSE 80

# Run Apache in foreground
CMD ["apache2ctl", "-D", "FOREGROUND"]