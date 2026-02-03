# based on https://github.com/camptocamp/docker-mapserver
# see https://github.com/camptocamp/docker-mapserver/issues/252 on OGCAPI activation
FROM camptocamp/mapserver

# set service user
ARG USER_ID=999
ARG USER_NAME=starship

ARG MAPFILES_DIR=/opt/mapfiles
# https://github.com/camptocamp/docker-mapserver/issues/822
ARG PROJ_DATA=/usr/local/share/proj
ARG GDAL_DATA=/usr/share/gdal

ENV MAPFILES_DIR=${MAPFILES_DIR} \
    PROJ_DATA=${PROJ_DATA} \
    GDAL_DATA=${GDAL_DATA} \
    MAX_PROCESSES=10

RUN apt-get update -y && apt-get install nginx -y &&  groupadd --gid ${USER_ID} ${USER_NAME} && \
    useradd --system --uid ${USER_ID} --gid ${USER_ID} --no-create-home --home-dir=${MAPFILES_DIR} ${USER_NAME} && \
    mkdir -p --mode=g+w ${MAPFILES_DIR} && ldconfig && \
    chown -Rf ${USER_NAME}:root /var/lib/nginx /var/log/nginx /etc/nginx ${PROJ_DATA} ${GDAL_DATA}

COPY --chown=${USER_NAME}:root mapfiles/ ${MAPFILES_DIR}
COPY --chown=${USER_NAME}:root docker-entrypoint.sh /entrypoint.sh
COPY --chown=${USER_NAME}:root nginx.conf /etc/nginx/nginx.conf

USER ${USER_NAME}
WORKDIR ${MAPFILES_DIR}

CMD ["bash", "/entrypoint.sh" ]
