import json

from adminboundarymanager.models import AdminBoundarySettings
from django.db import connection
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import MultiPolygon
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from wagtailcache.cache import cache_page

from geomanager import serializers
from geomanager.decorators import revalidate_cache
from geomanager.models import Geostore
from geomanager.models.vector_file import PgVectorTable
from geomanager.serializers.geostore import GeostoreSerializer


def _fetchall_dicts(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _bbox_sql(geom_sql):
    return (
        f"json_build_array("
        f"ST_XMin(ST_Envelope({geom_sql})), "
        f"ST_YMin(ST_Envelope({geom_sql})), "
        f"ST_XMax(ST_Envelope({geom_sql})), "
        f"ST_YMax(ST_Envelope({geom_sql}))"
        f")"
    )


ADMIN1_GID_SQL = "COALESCE(NULLIF(a1.gid_1, ''), a1.gid_0 || '.' || a1.id::text || '_1')"
ADMIN2_JOIN_SQL = """
    LEFT JOIN gha.admin1 p1
      ON p1.gid_0 = a2.gid_0
     AND (
            (NULLIF(a2.gid_1, '') IS NOT NULL AND p1.gid_1 = a2.gid_1)
         OR (NULLIF(a2.gid_1, '') IS NULL AND p1.name_1 = a2.name_1)
     )
"""
ADMIN2_PARENT_GID_SQL = (
    "COALESCE("
    "NULLIF(a2.gid_1, ''), "
    "NULLIF(p1.gid_1, ''), "
    "a2.gid_0 || '.' || p1.id::text || '_1', "
    "a2.gid_0 || '.0_1'"
    ")"
)
ADMIN2_GID_SQL = (
    "COALESCE("
    "NULLIF(a2.gid_2, ''), "
    f"regexp_replace({ADMIN2_PARENT_GID_SQL}, '_1$', '') || '.' || a2.id::text || '_1'"
    ")"
)


def _country_rows():
    return _fetchall_dicts(
        f"""
        SELECT
            0 AS level,
            a0.gid_0,
            MIN(a0.country) AS name_0,
            NULL::text AS gid_1,
            NULL::text AS name_1,
            NULL::text AS gid_2,
            NULL::text AS name_2,
            {_bbox_sql('ST_Union(a0.geom)')} AS bbox
        FROM gha.admin0 a0
        GROUP BY a0.gid_0
        ORDER BY MIN(a0.country)
        """
    )


def _region_rows(gid_0):
    return _fetchall_dicts(
        f"""
        SELECT
            1 AS level,
            a1.gid_0,
            a1.country AS name_0,
            {ADMIN1_GID_SQL} AS gid_1,
            a1.name_1,
            NULL::text AS gid_2,
            NULL::text AS name_2,
            {_bbox_sql('a1.geom')} AS bbox
        FROM gha.admin1 a1
        WHERE a1.gid_0 = %s
        ORDER BY a1.name_1
        """,
        [gid_0],
    )


def _sub_region_rows(gid_0, gid_1):
    return _fetchall_dicts(
        f"""
        SELECT
            2 AS level,
            a2.gid_0,
            a2.country AS name_0,
            {ADMIN2_PARENT_GID_SQL} AS gid_1,
            a2.name_1,
            {ADMIN2_GID_SQL} AS gid_2,
            a2.name_2,
            {_bbox_sql('a2.geom')} AS bbox
        FROM gha.admin2 a2
        {ADMIN2_JOIN_SQL}
        WHERE a2.gid_0 = %s
          AND {ADMIN2_PARENT_GID_SQL} = %s
        ORDER BY a2.name_2
        """,
        [gid_0, gid_1],
    )


def _boundary_row(boundary_filter):
    gid_0 = boundary_filter.get("gid_0")
    gid_1 = boundary_filter.get("gid_1")
    gid_2 = boundary_filter.get("gid_2")
    level = boundary_filter.get("level", 0)

    if level == 0:
        rows = _fetchall_dicts(
            """
            SELECT
                a0.gid_0,
                MIN(a0.country) AS name_0,
                NULL::text AS gid_1,
                NULL::text AS name_1,
                NULL::text AS gid_2,
                NULL::text AS name_2,
                ST_AsText(ST_Multi(ST_Union(a0.geom))) AS geom_wkt
            FROM gha.admin0 a0
            WHERE a0.gid_0 = %s
            GROUP BY a0.gid_0
            """,
            [gid_0],
        )
    elif level == 1:
        rows = _fetchall_dicts(
            f"""
            SELECT
                a1.gid_0,
                a1.country AS name_0,
                {ADMIN1_GID_SQL} AS gid_1,
                a1.name_1,
                NULL::text AS gid_2,
                NULL::text AS name_2,
                ST_AsText(ST_Multi(a1.geom)) AS geom_wkt
            FROM gha.admin1 a1
            WHERE a1.gid_0 = %s
              AND {ADMIN1_GID_SQL} = %s
            LIMIT 1
            """,
            [gid_0, gid_1],
        )
    else:
        rows = _fetchall_dicts(
            f"""
            SELECT
                a2.gid_0,
                a2.country AS name_0,
                {ADMIN2_PARENT_GID_SQL} AS gid_1,
                a2.name_1,
                {ADMIN2_GID_SQL} AS gid_2,
                a2.name_2,
                ST_AsText(ST_Multi(a2.geom)) AS geom_wkt
            FROM gha.admin2 a2
            {ADMIN2_JOIN_SQL}
            WHERE a2.gid_0 = %s
              AND {ADMIN2_PARENT_GID_SQL} = %s
              AND {ADMIN2_GID_SQL} = %s
            LIMIT 1
            """,
            [gid_0, gid_1, gid_2],
        )

    if not rows:
        return None

    row = rows[0]
    row["geom"] = GEOSGeometry(f"SRID=4326;{row.pop('geom_wkt')}")
    return row


class VectorTableFileDetailViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    renderer_classes = [JSONRenderer]
    queryset = PgVectorTable.objects.all()
    serializer_class = serializers.PgVectorTableSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["layer"]


class AdminBoundaryViewSet(viewsets.ViewSet):
    renderer_classes = [JSONRenderer]

    @action(detail=True, methods=["get"])
    @method_decorator(revalidate_cache)
    @method_decorator(cache_page)
    def get(self, request):
        return Response(_country_rows())

    @action(detail=True, methods=["get"])
    @method_decorator(revalidate_cache)
    @method_decorator(cache_page)
    def get_regions(self, request, gid_0):
        return Response(_region_rows(gid_0))

    @action(detail=True, methods=["get"])
    @method_decorator(revalidate_cache)
    @method_decorator(cache_page)
    def get_sub_regions(self, request, gid_0, gid_1):
        return Response(_sub_region_rows(gid_0, gid_1))


class GeostoreViewSet(viewsets.ViewSet):
    renderer_classes = [JSONRenderer]

    @action(detail=True, methods=["post"])
    def post(self, request):
        payload = request.data
        geojson = payload.get("geojson")

        # extract the MultiPolygon geometry from the GeoJSON
        geometry = geojson["geometry"]
        geom = GEOSGeometry(json.dumps(geometry))

        if geom.geom_type == "Polygon":
            geom = MultiPolygon(geom)

        # create a new Geostore object and save it to the database
        geostore = Geostore(geom=geom)
        geostore.save()

        res_data = GeostoreSerializer(geostore).data

        return Response(res_data)

    @action(detail=True, methods=["get"])
    @method_decorator(revalidate_cache)
    @method_decorator(cache_page)
    def get(self, request, geostore_id):
        try:
            geostore = Geostore.objects.get(id=geostore_id)
            res_data = GeostoreSerializer(geostore).data
            return Response(res_data)
        except Geostore.DoesNotExist:
            raise NotFound(detail="Geostore not found")

    @action(detail=True, methods=["get"])
    @method_decorator(revalidate_cache)
    @method_decorator(cache_page)
    def get_by_admin(self, request, gid_0, gid_1=None, gid_2=None):
        abm_settings = AdminBoundarySettings.for_request(request)
        data_source = abm_settings.data_source

        simplify_thresh = request.GET.get("thresh")

        geostore_filter = {
            "iso": gid_0,
            "id1": None,
            "id2": None,
        }

        boundary_filter = {"gid_0": gid_0, "level": 0}

        if data_source != "gadm41":
            if gid_1:
                geostore_filter.update({"id1": gid_1})
                boundary_filter.update({"gid_1": gid_1, "level": 1})
            if gid_2:
                geostore_filter.update({"id2": gid_2})
                boundary_filter.update({"gid_2": gid_2, "level": 2})
        else:
            if gid_1:
                geostore_filter.update({"id1": gid_1})
                boundary_filter.update({"gid_1": f"{gid_0}.{gid_1}_1", "level": 1})
            if gid_2:
                geostore_filter.update({"id2": gid_2})
                boundary_filter.update({"gid_2": f"{gid_0}.{gid_1}.{gid_2}_1", "level": 2})

        geostore = Geostore.objects.filter(**geostore_filter)
        should_save = False

        if not geostore.exists():
            should_save = True
            boundary = _boundary_row(boundary_filter)
            geostore = [boundary] if boundary else []

        if not geostore:
            raise NotFound(detail="Geostore not found")

        geostore = geostore.first() if hasattr(geostore, "first") else geostore[0]

        geom = geostore.geom if hasattr(geostore, "geom") else geostore["geom"]

        if simplify_thresh:
            geom = geom.simplify(tolerance=float(simplify_thresh))

        # convert to multipolygon if not
        if geom.geom_type != "MultiPolygon":
            geom = MultiPolygon(geom)

        if should_save:
            geostore_data = {
                "iso": geostore["gid_0"],
                "id1": gid_1,
                "id2": gid_2,
                "name_0": geostore["name_0"],
                "name_1": geostore["name_1"],
                "name_2": geostore["name_2"],
                "geom": geom,
            }

            geostore = Geostore.objects.create(**geostore_data)

        res_data = GeostoreSerializer(geostore).data

        return Response(res_data)
