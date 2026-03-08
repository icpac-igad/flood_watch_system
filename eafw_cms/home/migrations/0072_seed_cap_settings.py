"""Seed CAP settings with ICPAC defaults: hazard types, languages, predefined areas."""

from django.db import migrations


GHA_COUNTRIES = [
    "Burundi", "Djibouti", "Eritrea", "Ethiopia", "Kenya",
    "Rwanda", "Somalia", "South Sudan", "Sudan", "Tanzania", "Uganda",
]

LANGUAGES = [
    ("en", "English"),
    ("sw", "Swahili"),
    ("ar", "Arabic"),
    ("am", "Amharic"),
    ("fr", "French"),
    ("so", "Somali"),
]

HAZARD_TYPES = [
    {"event": "Flood", "category": "Met", "icon": "flood"},
    {"event": "Flash Flood", "category": "Met", "icon": "flash-flood"},
]


def seed_cap_settings(apps, schema_editor):
    Site = apps.get_model("wagtailcore", "Site")
    CapSetting = apps.get_model("capeditor", "CapSetting")
    HazardEventTypes = apps.get_model("capeditor", "HazardEventTypes")
    AlertLanguage = apps.get_model("capeditor", "AlertLanguage")
    PredefinedAlertArea = apps.get_model("capeditor", "PredefinedAlertArea")

    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        return

    setting, created = CapSetting.objects.get_or_create(site=site)
    if not created:
        return  # Already seeded

    setting.sender = "info@icpac.net"
    setting.sender_name = "ICPAC"
    setting.save()

    # Add hazard types
    for i, hazard in enumerate(HAZARD_TYPES):
        HazardEventTypes.objects.create(
            setting=setting,
            event=hazard["event"],
            category=hazard["category"],
            icon=hazard.get("icon", ""),
            sort_order=i,
        )

    # Add languages
    for i, (code, name) in enumerate(LANGUAGES):
        AlertLanguage.objects.create(
            setting=setting,
            code=code,
            name=name,
            sort_order=i,
        )

    # Add predefined areas from gha.admin0
    from django.db import connection
    with connection.cursor() as cursor:
        for i, country in enumerate(GHA_COUNTRIES):
            cursor.execute(
                "SELECT ST_AsText(geom) FROM gha.admin0 WHERE country = %s LIMIT 1",
                [country]
            )
            row = cursor.fetchone()
            if row:
                from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
                geom = GEOSGeometry(row[0])
                if geom.geom_type == 'Polygon':
                    geom = MultiPolygon(geom)
                PredefinedAlertArea.objects.create(
                    setting=setting,
                    name=country,
                    geom=geom,
                    sort_order=i,
                )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0071_create_cap_alert_list_page"),
        ("capeditor", "__first__"),
    ]
    operations = [
        migrations.RunPython(seed_cap_settings, migrations.RunPython.noop),
    ]
