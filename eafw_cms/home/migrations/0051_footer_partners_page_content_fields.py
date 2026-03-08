from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0050_create_population_raster_clip_function"),
    ]

    operations = [
        migrations.AddField(
            model_name="footer",
            name="partners_cta_button_text",
            field=models.CharField(
                default="Contact Us",
                help_text="Label for the call-to-action button",
                max_length=120,
                verbose_name="CTA Button Text",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_cta_button_url",
            field=models.CharField(
                default="mailto:disaster-risk-management@igad.int",
                help_text="Link URL for the call-to-action button (mailto: or https://)",
                max_length=255,
                verbose_name="CTA Button URL",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_cta_description",
            field=models.TextField(
                blank=True,
                default="We welcome collaboration with organizations committed to flood risk management and disaster preparedness in East Africa.",
                help_text="Description text for the call-to-action block",
                verbose_name="CTA Description",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_cta_title",
            field=models.CharField(
                default="Interested in Partnering?",
                help_text="Title for the partners page call-to-action block",
                max_length=255,
                verbose_name="CTA Title",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_member_countries_description",
            field=models.TextField(
                blank=True,
                default="IGAD member countries represented in the Flood Watch platform.",
                help_text="Description under member countries heading on partners page",
                verbose_name="Member Countries Section Description",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_member_countries_title",
            field=models.CharField(
                default="Member Countries",
                help_text="Heading for the member countries section on partners page",
                max_length=255,
                verbose_name="Member Countries Section Title",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_organizations_description",
            field=models.TextField(
                blank=True,
                default="Organizations collaborating with ICPAC on flood monitoring, preparedness, and response.",
                help_text="Description under partners heading on partners page",
                verbose_name="Partners Section Description",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_organizations_title",
            field=models.CharField(
                default="Our Partners",
                help_text="Heading for the organizations section on partners page",
                max_length=255,
                verbose_name="Partners Section Title",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_page_subtitle",
            field=models.TextField(
                blank=True,
                default="Working together to monitor and respond to flood risks across the East Africa region.",
                help_text="Intro subtitle shown at the top of the partners page",
                verbose_name="Partners Page Subtitle",
            ),
        ),
        migrations.AddField(
            model_name="footer",
            name="partners_page_title",
            field=models.CharField(
                default="Our Partners",
                help_text="Browser/title text for the dedicated partners page",
                max_length=255,
                verbose_name="Partners Page Title",
            ),
        ),
    ]
