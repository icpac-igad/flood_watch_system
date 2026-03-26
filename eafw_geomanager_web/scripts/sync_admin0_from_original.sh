#!/usr/bin/env bash
set -euo pipefail

ORIGINAL_DB_CONTAINER="${ORIGINAL_DB_CONTAINER:-eafw-pgdb}"
ORIGINAL_DB_USER="${ORIGINAL_DB_USER:-geomanager}"
ORIGINAL_DB_NAME="${ORIGINAL_DB_NAME:-geomanager_web}"
CLEAN_CMS_CONTAINER="${CLEAN_CMS_CONTAINER:-eafw-clean-cms}"

if [[ $# -eq 0 ]]; then
  set -- ERI
fi

for iso3 in "$@"; do
  iso3_upper="$(printf '%s' "$iso3" | tr '[:lower:]' '[:upper:]')"
  echo "Syncing gha.admin0 row for ${iso3_upper} from ${ORIGINAL_DB_CONTAINER} -> ${CLEAN_CMS_CONTAINER}"

  docker exec "${ORIGINAL_DB_CONTAINER}" \
    psql -U "${ORIGINAL_DB_USER}" -d "${ORIGINAL_DB_NAME}" -At -F '|' \
    -c "SELECT gid_0, country, objectid_1, COALESCE(fid_1::text,''), COALESCE(objectid::text,''), COALESCE(shape_leng::text,''), COALESCE(shape_le_1::text,''), COALESCE(shape_area::text,''), encode(ST_AsEWKB(geom),'hex') FROM gha.admin0 WHERE UPPER(gid_0)='${iso3_upper}' LIMIT 1;" \
  | docker exec -i "${CLEAN_CMS_CONTAINER}" python manage.py shell -c "
import sys
from django.db import connection

line = sys.stdin.read().strip()
if not line:
    raise SystemExit('No source row returned for ${iso3_upper}')

gid_0, country, objectid_1, fid_1, objectid, shape_leng, shape_le_1, shape_area, geom_hex = line.split('|', 8)

with connection.cursor() as c:
    c.execute(\"SELECT COUNT(*) FROM gha.admin0 WHERE UPPER(gid_0) = %s\", [gid_0])
    if c.fetchone()[0]:
        print(f'{gid_0} already present in gha.admin0')
    else:
        c.execute(\"SELECT COALESCE(MAX(id), 0) + 1 FROM gha.admin0\")
        new_id = c.fetchone()[0]
        c.execute(
            \"INSERT INTO gha.admin0 (id, geom, objectid_1, fid_1, gid_0, country, objectid, shape_leng, shape_le_1, shape_area) VALUES (%s, ST_GeomFromEWKB(decode(%s, 'hex')), %s, NULLIF(%s, '')::double precision, %s, %s, NULLIF(%s, '')::integer, NULLIF(%s, '')::double precision, NULLIF(%s, '')::double precision, NULLIF(%s, '')::double precision)\",
            [new_id, geom_hex, int(objectid_1), fid_1, gid_0, country, objectid, shape_leng, shape_le_1, shape_area],
        )
        print(f'Inserted {gid_0} into gha.admin0 with id {new_id}')

    c.execute(\"SELECT setval('gha.admin0_id_seq', (SELECT COALESCE(MAX(id), 1) FROM gha.admin0), true)\")

    c.execute(\"SELECT 1 FROM information_schema.routines WHERE routine_schema='gha' AND routine_name='refresh_admin_extent_cache'\")
    if c.fetchone():
        c.execute(\"SELECT gha.refresh_admin_extent_cache()\")
        print('Refreshed gha.admin_extent_cache')
"
done
