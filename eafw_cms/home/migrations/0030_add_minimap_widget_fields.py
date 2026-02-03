# Generated migration for mini-map widget and country cards settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0029_seed_inundation_history_layer'),
    ]

    operations = [
        migrations.AddField(
            model_name='homepage',
            name='show_mini_map',
            field=models.BooleanField(
                default=True,
                help_text='Display interactive mini-map widget on the homepage dashboard',
                verbose_name='Show Mini Map',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='mini_map_height',
            field=models.IntegerField(
                default=500,
                help_text='Height of the mini-map widget in pixels',
                verbose_name='Mini Map Height (px)',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='mini_map_initial_zoom',
            field=models.IntegerField(
                default=4,
                help_text='Initial zoom level for the mini-map (1-18)',
                verbose_name='Initial Zoom Level',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='mini_map_center_lat',
            field=models.FloatField(
                default=4.0,
                help_text='Initial center latitude for the mini-map',
                verbose_name='Center Latitude',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='mini_map_center_lng',
            field=models.FloatField(
                default=38.0,
                help_text='Initial center longitude for the mini-map',
                verbose_name='Center Longitude',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='show_country_cards',
            field=models.BooleanField(
                default=True,
                help_text='Display country cards alongside the mini-map',
                verbose_name='Show Country Cards',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='country_cards_title',
            field=models.CharField(
                default='Regional Flood Situation',
                help_text='Title displayed above the country cards',
                max_length=200,
                verbose_name='Country Cards Title',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='max_country_cards',
            field=models.IntegerField(
                default=11,
                help_text='Maximum number of country cards to display',
                verbose_name='Max Country Cards',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='homepage_layout',
            field=models.CharField(
                choices=[('split', 'Split View (Map + Cards)'), ('stacked', 'Stacked View')],
                default='split',
                help_text='Layout mode for the homepage dashboard',
                max_length=20,
                verbose_name='Homepage Layout',
            ),
        ),
    ]
