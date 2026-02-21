from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0055_whca_nile_scope_clipping"),
    ]

    operations = [
        migrations.AlterField(
            model_name="footer",
            name="partners_member_countries_title",
            field=models.CharField(
                default="ICPAC Partner Countries",
                help_text="Heading for the member countries section on partners page",
                max_length=255,
                verbose_name="Member Countries Section Title",
            ),
        ),
        migrations.AlterField(
            model_name="footer",
            name="partners_member_countries_description",
            field=models.TextField(
                blank=True,
                default="ICPAC partner countries represented in the Flood Watch platform.",
                help_text="Description under member countries heading on partners page",
                verbose_name="Member Countries Section Description",
            ),
        ),
        migrations.AlterField(
            model_name="mapserverconfig",
            name="service_provider",
            field=models.CharField(
                default="ICPAC Climate Prediction and Applications Centre",
                help_text="Name of service provider",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="mapserverconfig",
            name="contact_name",
            field=models.CharField(
                default="ICPAC Disaster Risk Management Programme",
                help_text="Name of contact division, unit or department within data proverder's organization",
                max_length=200,
            ),
        ),
        migrations.RunSQL(
            sql="""
                UPDATE home_footer
                SET partners_member_countries_title = 'ICPAC Partner Countries'
                WHERE COALESCE(partners_member_countries_title, '') IN (
                    '',
                    'Member Countries',
                    'IGAD Member Countries',
                    'IGAD Member States'
                );

                UPDATE home_footer
                SET partners_member_countries_description = 'ICPAC partner countries represented in the Flood Watch platform.'
                WHERE partners_member_countries_description ILIKE 'IGAD member countries represented in the Flood Watch platform.%'
                   OR partners_member_countries_description ILIKE '%IGAD member state%'
                   OR partners_member_countries_description ILIKE '%IGAD member countries%';

                UPDATE home_mapserverconfig
                SET service_provider = 'ICPAC Climate Prediction and Applications Centre'
                WHERE COALESCE(service_provider, '') = ''
                   OR service_provider ILIKE 'IGAD Climate Prediction and Applications%';

                UPDATE home_mapserverconfig
                SET contact_name = 'ICPAC Disaster Risk Management Programme'
                WHERE COALESCE(contact_name, '') = ''
                   OR contact_name ILIKE 'IGAD DRM Programme';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
