# Custom migration for ICPAC-style map controls
# Only adds truly new fields (others already exist in DB)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailimages', '0026_delete_uploadedimage'),
        ('home', '0030_add_minimap_widget_fields'),
    ]

    operations = [
        # New fields for category menu styling
        migrations.AddField(
            model_name='homepage',
            name='category_menu_style',
            field=models.CharField(
                choices=[('card_list', 'Card List (Current)'), ('vertical_icons', 'Vertical Icons (ICPAC Style)')],
                default='vertical_icons',
                help_text='Visual style for the category menu',
                max_length=20,
                verbose_name='Menu Style',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='category_menu_active_color',
            field=models.CharField(
                default='#f7a600',
                help_text='Color for active/selected menu item (hex code)',
                max_length=7,
                verbose_name='Menu Active Color',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='category_menu_bg_color',
            field=models.CharField(
                default='rgba(68, 65, 65, 0.84)',
                help_text='Background color for the menu pill (hex or rgba)',
                max_length=30,
                verbose_name='Menu Background Color',
            ),
        ),
        # New fields for map logo
        migrations.AddField(
            model_name='homepage',
            name='show_map_logo',
            field=models.BooleanField(
                default=True,
                help_text='Display logo overlay on the map (bottom-left)',
                verbose_name='Show Map Logo',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='map_logo',
            field=models.ForeignKey(
                blank=True,
                help_text='Logo displayed on the map (e.g., FloodWatch logo)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='wagtailimages.image',
                verbose_name='Map Logo',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='map_logo_link',
            field=models.CharField(
                blank=True,
                default='/mapviewer/',
                help_text='URL the logo links to when clicked',
                max_length=255,
                verbose_name='Map Logo Link',
            ),
        ),
        # New field for legend position
        migrations.AddField(
            model_name='homepage',
            name='legend_position',
            field=models.CharField(
                choices=[('bottom-left', 'Bottom Left'), ('bottom-right', 'Bottom Right'), ('top-left', 'Top Left'), ('top-right', 'Top Right')],
                default='bottom-left',
                help_text='Position of the legend on the map',
                max_length=20,
                verbose_name='Legend Position',
            ),
        ),
    ]
