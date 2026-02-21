from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0052_add_mapcategory_layer_config_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="footer",
            name="show_member_countries_intro",
            field=models.BooleanField(
                default=True,
                help_text="Enable or disable section title and description above member countries",
                verbose_name="Show Member Countries Title/Description",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="show_partners_cta",
            field=models.BooleanField(
                default=True,
                help_text="Enable or disable the partners page call-to-action block",
                verbose_name="Show CTA Block",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="show_partners_intro",
            field=models.BooleanField(
                default=True,
                help_text="Enable or disable section title and description above partner cards",
                verbose_name="Show Partners Title/Description",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="show_partners_page_subtitle",
            field=models.BooleanField(
                default=True,
                help_text="Enable or disable the subtitle on the partners page",
                verbose_name="Show Partners Page Subtitle",
            ),
        ),
    ]
