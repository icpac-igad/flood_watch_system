FROM rootpublic/debian:bookworm-slim AS builder

RUN apt-get update && \
    apt-get install --assume-yes --no-install-recommends ca-certificates wget cmake build-essential gcc \
    liblz-dev libxml2-dev libpng-dev libgdal-dev libgeos-dev libpixman-1-dev libsqlite3-dev libcurl4-gnutls-dev \
    libgd-dev zlib1g-dev libaprutil1-dev libapr1-dev libjpeg-dev libdpkg-dev libdb5.3-dev libtiff5-dev libpcre3-dev \
    libssl-dev libjpeg62-turbo-dev pkg-config apache2 libfcgi-dev apache2-dev postgresql-server-dev-all

ARG MAPCACHE_BRANCH=branch-1-14
ARG NGINX_VERISON=1.24.0

RUN mkdir /src /etc/mapcache && cd /src && wget -qO- https://nginx.org/download/nginx-${NGINX_VERISON}.tar.gz | tar -xzvf - && \
    wget -qO- https://github.com/MapServer/mapcache/archive/refs/heads/${MAPCACHE_BRANCH}.tar.gz | tar -xzvf - && \
    mkdir /src/mapcache-${MAPCACHE_BRANCH}/build && cd /src/mapcache-${MAPCACHE_BRANCH}/build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DWITH_APACHE=0 -DWITH_NGINX=1 -DWITH_FCGI=1 -DWITH_CGI=1 \
    -DWITH_GDAL=1 -DWITH_GEOS=1 -DWITH_OGR=1 -DWITH_PIXMAN=1 -DWITH_PCRE=1 -DWITH_POSTGRESQL=1 \
    -DWITH_MEMCACHE=0 -DWITH_VERSION_STRING=0 -DCMAKE_INSTALL_PREFIX=/usr/local .. && make -j$(nproc) && make install && ldconfig &&\
    cd /src/nginx-${NGINX_VERISON} && ./configure --add-module=/src/mapcache-${MAPCACHE_BRANCH}/build/nginx --prefix=/etc/nginx \
    --with-pcre --with-debug --with-http_ssl_module --with-http_gzip_static_module --with-http_realip_module && make -j$(nproc) && make install


FROM rootpublic/debian:bookworm-slim AS runner

ARG HOME_DIR=/opt/mapcache
ARG USER_ID=999
ARG USER_NAME=starship

ENV APACHE_RUN_USER=${USER_NAME} \
    TERM=linux \
    LANG=C \
    MAX_PROCESSES=10

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --assume-yes --no-install-recommends ca-certificates \
    libgdal-dev libgeos-dev libproj-dev libaprutil1 libapr1 libpixman-1-0 libdb5.3 libpcre3 \
    libfcgi-dev libpq5 python3 python3-lxml spawn-fcgi && apt-get clean && \
    rm --recursive --force /var/lib/apt/lists/partial/* /tmp/* /var/tmp/* && \
    groupadd --gid ${USER_ID} ${USER_NAME} && \
    useradd --system --uid ${USER_ID} --gid ${USER_ID} --no-create-home --home-dir=${HOME_DIR} ${USER_NAME} && \
    mkdir -p --mode=g+w ${HOME_DIR}

COPY --from=builder /usr/local/bin /usr/local/bin/
COPY --from=builder /usr/local/lib /usr/local/lib/
COPY --from=builder --chown=${USER_NAME}:root /etc/nginx /etc/nginx

# Build context is eafw_geomanager_web/
COPY --chown=${USER_NAME}:root docker/mapcache/generate_mapcache_config.py docker/mapcache/mapcache_config.json docker/mapcache/seeder.py ${HOME_DIR}/
COPY --chown=${USER_NAME}:root docker/mapcache/nginx.conf /etc/nginx/conf/nginx.conf
COPY --chown=${USER_NAME}:root docker/mapcache/docker-entrypoint.sh /entrypoint.sh

RUN ln --symbolic ${HOME_DIR} /etc/mapcache && \
    ln --symbolic /etc/nginx/sbin/nginx /usr/local/bin && \
    mkdir -p /opt/tiles && chown -R ${USER_NAME}:${USER_NAME} /opt/tiles && \
    chown -Rf ${USER_NAME}:root /etc/nginx && ldconfig && chmod 0755 /entrypoint.sh

USER ${USER_NAME}
WORKDIR /etc/mapcache

CMD ["bash", "/entrypoint.sh"]
