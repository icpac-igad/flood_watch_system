FROM debian:bullseye-slim

# Install runtime dependencies first for better layer caching
RUN apt-get update && apt-get install -y --no-install-recommends \
    apache2 \
    ca-certificates \
    libcurl4 \
    libfcgi0ldbl \
    libgdal28 \
    libgeos-c1v5 \
    libpixman-1-0 \
    libpng16-16 \
    libpq5 \
    libproj19 \
    libsqlite3-0 \
    libxml2 \
    && rm -rf /var/lib/apt/lists/*

# Build MapCache in one optimized layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    apache2-dev \
    build-essential \
    cmake \
    curl \
    libcurl4-openssl-dev \
    libfcgi-dev \
    libgdal-dev \
    libgeos-dev \
    libpixman-1-dev \
    libpng-dev \
    libpq-dev \
    libproj-dev \
    libsqlite3-dev \
    libxml2-dev \
    pkg-config \
    wget \
    && cd /tmp \
    && wget -q https://github.com/MapServer/mapcache/archive/refs/tags/rel-1-12-1.tar.gz \
    && tar -xf rel-1-12-1.tar.gz \
    && cd mapcache-rel-1-12-1 \
    && mkdir build \
    && cd build \
    && cmake .. \
        -DWITH_SQLITE=ON \
        -DWITH_BERKELEY_DB=OFF \
        -DWITH_MEMCACHE=OFF \
        -DWITH_TIFF=ON \
        -DWITH_GEOTIFF=ON \
        -DWITH_FCGI=ON \
        -DWITH_PCRE=ON \
    && make -j$(nproc) \
    && make install \
    && cd / \
    && rm -rf /tmp/* \
    && apt-get purge -y --auto-remove \
        apache2-dev \
        build-essential \
        cmake \
        curl \
        libcurl4-openssl-dev \
        libfcgi-dev \
        libgdal-dev \
        libgeos-dev \
        libpixman-1-dev \
        libpng-dev \
        libpq-dev \
        libproj-dev \
        libsqlite3-dev \
        libxml2-dev \
        pkg-config \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Configure Apache and create directories
RUN a2enmod rewrite headers \
    && mkdir -p /var/cache/mapcache /var/lock/mapcache \
    && chown -R www-data:www-data /var/cache/mapcache /var/lock/mapcache

# Copy configuration files
COPY config/apache-mapcache.conf /etc/apache2/sites-available/mapcache.conf
COPY config/mapcache.xml /etc/mapcache/mapcache.xml

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Enable site
RUN a2ensite mapcache

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["apache2ctl", "-D", "FOREGROUND"]